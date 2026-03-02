import json
import os
import shutil

from zoia_lib.backend.api import PatchStorage
from zoia_lib.backend.patch import Patch
from zoia_lib.backend.patch_save import PatchSave
from zoia_lib.common import errors

ps = PatchStorage()


class PatchUpdate(Patch):
    """The PatchUpdate class is a child of the Patch class. It is
    responsible for patch and patch note updating operations.
    """

    def __init__(self):
        """Initialize the class such that it has a reference to the
        backend path.
        """

        super().__init__()

    def update_data(self, idx, data, mode):
        """Attempts to modify data to a patches metadata.

        idx: The id for the patch metadata that is to be modified.
        tag: A string representing the tag that is to be added. Does not
             necessarily need to be a single tag.
        mode: The type of data that is being added. Valid modes are:
              - 1 -> Modify the tags
              - 2 -> Modify the categories
              - 3 -> Modify the patch notes
              - 4 -> Modify the author
              - 5 -> Modify the patch title
              - 6 -> Modify the rating
        """

        # Lookup the right term to use.
        index = {
            1: "tags",
            2: "categories",
            3: "content",
            4: "author",
            5: "title",
            6: "rating",
        }[mode]

        # Get the patch name and id.
        pch = idx
        idx = idx.split("_")[0]

        # Update the key with the new data.
        with open(os.path.join(self.back_path, idx, "{}.json".format(pch)), "r") as f:
            temp = json.loads(f.read())
        # if mode == 4:
        #    temp[index]["name"] = data
        temp[index] = data
        with open(os.path.join(self.back_path, idx, "{}.json".format(pch)), "w") as f:
            f.write(json.dumps(temp))

    def check_for_updates(self):
        """Upon startup, automatically retrieve the latest version of
        patches from PS, should any that have been previously downloaded
        are updated.

        This method will check the updated_at attribute of each
        downloaded patch, should this differ compared to what is
        returned by PS, a new patch will attempt to be saved. If the
        binary file is determined to be identical to the one stored
        within the backend, the saving is aborted at there was no update
        to the patch itself. Otherwise, a new version of the patch is
        added and saved within the patch directory.

        return: A tuple containing the number of patches that updated as
                an int as the first element, and the names of the
                patches that updated in as strings in an array as the
                second element.
        """

        meta = []

        for patch in os.listdir(self.back_path):
            # Only check for updates for patches hosted on PS
            # (denoted via the 6-digit ID numbers).
            # Exclude any special dirs in the backend.
            if (
                os.path.isdir(os.path.join(self.back_path, patch))
                and len(patch) > 5
                and patch != "art_cache"
                and patch != "Banks"
                and patch != "Editor"
                and patch != "Folders"
                and patch != ".DS_Store"
                and patch != "Samples"
            ):
                patch_dir = os.path.join(self.back_path, patch)
                json_files = [f for f in os.listdir(patch_dir) if f.endswith(".json")]
                if not json_files:
                    continue

                # Determine the newest stored revision for this patch id.
                # Single-version linked patches are stored as id.json,
                # version histories are stored as id_vN.json.
                latest_json = None
                latest_revision = -1
                for json_name in json_files:
                    stem = json_name[:-5]
                    rev = -1
                    if stem == patch:
                        rev = 0
                    elif stem.startswith(patch + "_v"):
                        suffix = stem.split("_v")[-1]
                        if suffix.isdigit():
                            rev = int(suffix)
                    if rev > latest_revision:
                        latest_revision = rev
                        latest_json = json_name
                if latest_json is None:
                    continue

                with open(os.path.join(patch_dir, latest_json), "r") as f:
                    temp = json.loads(f.read())
            else:
                continue
            # Only need the id and updated_at for comparison purposes.
            meta_small = {"id": temp["id"], "updated_at": temp["updated_at"]}
            meta.append(meta_small)

        # Get a list of binary/metadata for all files that have been updated
        # on PatchStorage.
        pch_list = ps.get_potential_updates(meta)

        def _latest_json_path_for_patch(patch_id: str):
            patch_dir = os.path.join(self.back_path, patch_id)
            if not os.path.isdir(patch_dir):
                return None
            json_files = [f for f in os.listdir(patch_dir) if f.endswith(".json")]
            if not json_files:
                return None

            latest_json = None
            latest_revision = -1
            for json_name in json_files:
                stem = json_name[:-5]
                rev = -1
                if stem == patch_id:
                    rev = 0
                elif stem.startswith(patch_id + "_v"):
                    suffix = stem.split("_v")[-1]
                    if suffix.isdigit():
                        rev = int(suffix)
                if rev > latest_revision:
                    latest_revision = rev
                    latest_json = json_name
            if latest_json is None:
                return None
            return os.path.join(patch_dir, latest_json)

        # Try to save the new binaries to the backend.
        save = PatchSave()
        pchs = []
        for patch in pch_list:
            try:
                save.save_to_backend(patch[0])
            except errors.SavingError:
                # Same binary, but patch notes are different, update those.
                idx = str(patch[1]["id"])
                json_path = _latest_json_path_for_patch(idx)
                if json_path is None:
                    raise errors.BadPathError(idx, 301)

                with open(json_path, "r") as f:
                    local_meta = json.loads(f.read())

                # Keep local-only fields while refreshing upstream metadata.
                fresh_meta = patch[1]
                if "rating" in local_meta:
                    fresh_meta["rating"] = local_meta["rating"]
                if "downloaded_at" in local_meta:
                    fresh_meta["downloaded_at"] = local_meta["downloaded_at"]

                with open(json_path, "w") as f:
                    f.write(json.dumps(fresh_meta))
                pchs.append(patch[1]["title"])
            else:
                pchs.append(patch[1]["title"])

        # Pass the number of updates and titles of patches updated.
        return len(pch_list), pchs

    def convert_local_to_ps(self, src: str, dest: str):
        """Converts 5-digit local file to 6-digit PS file after a successful upload."""

        # Move files to new dir
        shutil.move(os.path.join(self.back_path, src),
                    os.path.join(self.back_path, dest))

        # Rename bin
        os.rename(os.path.join(self.back_path, dest, "{}.bin".format(src)),
                  os.path.join(self.back_path, dest, "{}.bin".format(dest)))

        # Drop the json, we'll grab it from the API
        os.remove(os.path.join(self.back_path, dest, "{}.json".format(src)))

        return ps.get_patch_meta(dest)

    def split_version_history(self, patch_id: str, versions=None):
        """Splits a version-history patch directory into standalone local patches.

        patch_id: The 6-digit PS patch id directory to split.
        versions: Optional list of version stems to split (e.g., ["123456", "123456_v2"]).
        return: List of new 5-digit patch ids created.
        """

        patch_dir = os.path.join(self.back_path, patch_id)
        if not os.path.isdir(patch_dir):
            raise errors.BadPathError(patch_dir, 301)

        json_files = [f for f in os.listdir(patch_dir) if f.endswith(".json")]
        if not json_files:
            raise errors.BadPathError(patch_dir, 301)

        existing_ids = {
            d
            for d in os.listdir(self.back_path)
            if os.path.isdir(os.path.join(self.back_path, d))
            and d.isdigit()
            and len(d) == 5
        }

        def _generate_unique_local_id(seed: str):
            attempt = 0
            while True:
                patch_id = str(abs(hash(seed if attempt == 0 else f"{seed}_{attempt}")))
                if len(patch_id) > 5:
                    patch_id = patch_id[:5]
                while len(patch_id) < 5:
                    patch_id += "0"
                if patch_id not in existing_ids:
                    return patch_id
                attempt += 1

        versions_found = []
        for json_name in json_files:
            stem = json_name[:-5]
            bin_name = "{}.bin".format(stem)
            bin_path = os.path.join(patch_dir, bin_name)
            if not os.path.isfile(bin_path):
                raise errors.BadPathError(bin_path, 301)
            v_num = 1
            if "_v" in stem:
                suffix = stem.split("_v")[-1]
                if suffix.isdigit():
                    v_num = int(suffix)
            versions_found.append((v_num, json_name, bin_name, stem))

        versions_found.sort(key=lambda item: item[0])
        all_versions = list(versions_found)
        if versions is not None:
            version_set = set(versions)
            versions_found = [v for v in versions_found if v[3] in version_set]
            if not versions_found:
                return []

        # Keep one linked PS patch when splitting all selected versions so the
        # app still recognizes the patch as downloaded and can update it.
        if patch_id.isdigit() and len(patch_id) == 6 and len(versions_found) == len(all_versions):
            if len(versions_found) <= 1:
                return []
            # versions_found is sorted oldest -> newest; keep newest linked.
            versions_found = versions_found[:-1]

        def _title_from_filename(filename: str):
            base, _ext = os.path.splitext(filename)
            if "_" in base and len(base.split("_")[0]) == 3:
                try:
                    float(base.split("_")[0])
                    base = base[4:]
                except ValueError:
                    pass
            if base.startswith("zoia_"):
                base = base[5:]
            base = base.replace("_", " ").strip()
            return base

        new_ids = []
        created_dirs = []
        try:
            for _, json_name, bin_name, stem in versions_found:
                new_id = _generate_unique_local_id(os.path.join(patch_dir, json_name))
                existing_ids.add(new_id)
                dest_dir = os.path.join(self.back_path, new_id)
                if os.path.exists(dest_dir):
                    raise errors.SavingError(new_id, 505)
                os.makedirs(dest_dir, exist_ok=False)
                created_dirs.append(dest_dir)

                with open(os.path.join(patch_dir, json_name), "r") as f:
                    meta = json.loads(f.read())
                meta["id"] = int(new_id)
                if "files" in meta and meta["files"]:
                    if isinstance(meta["files"][0], dict):
                        meta["files"][0]["id"] = int(new_id)
                        filename = meta["files"][0].get("filename", "")
                        if filename:
                            meta["title"] = _title_from_filename(filename)

                with open(os.path.join(dest_dir, "{}.json".format(new_id)), "w") as f:
                    json.dump(meta, f)

                shutil.copy2(
                    os.path.join(patch_dir, bin_name),
                    os.path.join(dest_dir, "{}.bin".format(new_id)),
                )
                new_ids.append(new_id)

                os.remove(os.path.join(patch_dir, json_name))
                os.remove(os.path.join(patch_dir, bin_name))

            remaining_json = [f for f in os.listdir(patch_dir) if f.endswith(".json")]
            if len(remaining_json) == 1:
                remaining_stem = remaining_json[0][:-5]
                src_json = os.path.join(patch_dir, remaining_stem + ".json")
                src_bin = os.path.join(patch_dir, remaining_stem + ".bin")

                # Keep title behavior consistent: use the version filename-derived
                # title even for the one patch that remains linked to the PS id.
                with open(src_json, "r") as f:
                    remaining_meta = json.loads(f.read())
                if "files" in remaining_meta and remaining_meta["files"]:
                    if isinstance(remaining_meta["files"][0], dict):
                        filename = remaining_meta["files"][0].get("filename", "")
                        if filename:
                            remaining_meta["title"] = _title_from_filename(filename)
                with open(src_json, "w") as f:
                    json.dump(remaining_meta, f)

                if remaining_stem != patch_id:
                    dest_json = os.path.join(patch_dir, patch_id + ".json")
                    dest_bin = os.path.join(patch_dir, patch_id + ".bin")
                    if not os.path.isfile(src_bin):
                        raise errors.BadPathError(src_bin, 301)
                    os.rename(src_json, dest_json)
                    os.rename(src_bin, dest_bin)
            elif not remaining_json:
                shutil.rmtree(patch_dir)
        except Exception:
            for d in created_dirs:
                if os.path.isdir(d):
                    shutil.rmtree(d, ignore_errors=True)
            raise

        return new_ids
