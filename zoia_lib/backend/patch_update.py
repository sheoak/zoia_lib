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
                and patch != "Folders"
                and patch != ".DS_Store"
                and patch != "Samples"
            ):
                # Split on number of versions in the dir.
                if (
                    len(os.listdir(os.path.join(self.back_path, patch))) > 2
                ):
                    # Multiple versions, only need the latest.
                    with open(
                        os.path.join(self.back_path, patch, "{}_v1.json".format(patch)), "r"
                    ) as f:
                        temp = json.loads(f.read())
                else:
                    # Just a single patch in the directory, easy.
                    with open(
                        os.path.join(self.back_path, patch, "{}.json".format(patch)), "r"
                    ) as f:
                        temp = json.loads(f.read())
            else:
                continue
            # Only need the id and updated_at for comparison purposes.
            meta_small = {"id": temp["id"], "updated_at": temp["updated_at"]}
            meta.append(meta_small)

        # Get a list of binary/metadata for all files that have been updated
        # on PatchStorage.
        pch_list = ps.get_potential_updates(meta)

        # Try to save the new binaries to the backend.
        save = PatchSave()
        pchs = []
        for patch in pch_list:
            try:
                save.save_to_backend(patch[0])
            except errors.SavingError:
                # Same binary, but patch notes are different, update those.
                idx = str(patch[1]["id"])
                try:
                    with open(
                        os.path.join(self.back_path, idx, "{}.bin".format(idx)), "w"
                    ) as f:
                        f.write(json.dumps(patch[1]))
                        pchs.append(patch[1]["title"])
                except FileNotFoundError:
                    with open(
                        os.path.join(self.back_path, idx, "{}_v1.bin".format(idx)), "r"
                    ) as f:
                        f.write(json.dumps(patch[1]))
                        pchs.append(patch[1]["title"])
            pchs.append(patch)

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
        if versions is not None:
            version_set = set(versions)
            versions_found = [v for v in versions_found if v[3] in version_set]
            if not versions_found:
                return []

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
            if not remaining_json:
                shutil.rmtree(patch_dir)
        except Exception:
            for d in created_dirs:
                if os.path.isdir(d):
                    shutil.rmtree(d, ignore_errors=True)
            raise

        return new_ids
