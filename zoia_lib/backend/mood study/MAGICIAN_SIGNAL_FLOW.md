# The Magician — signal flow

Decoded from `The_Magician.bin` (77 modules, 132 connections, 11 pages, 58.81% CPU).
Node labels are `name (module #)`.

> Vue joueur (sans détails de modules) : `MAGICIAN_SIGNAL_PATH.md`

## 1. Audio path

```mermaid
flowchart LR
    IN["In (32)<br/>Audio Input L/R"]

    subgraph LIVE["Live Route — page 1"]
        LDRY["Live Dry (33)<br/>VCA"]
        DSND["drySend (34)<br/>VCA"]
    end

    subgraph LOOPERS["Looper — page 4"]
        LPL["LoopL (47)<br/>Looper 16s · overdub"]
        LPR["LoopR (48)<br/>Looper 16s · overdub"]
        GRN["Grain (49)<br/>Granular · 3 grains"]
    end

    subgraph GRT["Granular Route — page 3"]
        GDIR["granDir (43)<br/>VCA"]
        GPAS["granPass (44)<br/>VCA"]
    end

    subgraph LRT["Loop Route — page 2"]
        LOUT["loopOut (38)<br/>VCA · L.Level"]
        LDIR["loopDir (39)<br/>VCA"]
        LSND["loopSend (40)<br/>VCA"]
    end

    subgraph FXP["FX — page 5"]
        DLY["Delay (50)<br/>Tape Delay w/Mod"]
        RVB["Reverb (51)<br/>Hall"]
        WOUT["wetOut (52)<br/>VCA"]
        RWET["recWet (53)<br/>VCA · FXLoop Send"]
    end

    OUT["Out (37)<br/>Audio Output · Volume"]

    IN --> LDRY --> OUT
    IN --> DSND --> DLY
    IN --> LPL
    IN --> LPR

    LPL --> GDIR
    LPR --> GDIR
    GDIR --> LOUT
    LPL --> GRN
    LPR --> GRN
    GRN --> GPAS --> LOUT

    LOUT --> LDIR --> OUT
    LOUT --> LSND --> DLY

    DLY --> RVB --> WOUT
    WOUT --> OUT
    WOUT --> RWET
    RWET -. "wet re-record" .-> LPL
    RWET -. "wet re-record" .-> LPR
```

Three things sum at the output: **live dry** (33), **loop dry** (39), **wet FX** (52).

## 2. Wet/dry crossfades (CV)

Every send/dry pair is a constant-power-ish crossfade: a Multiplier gates the
send level, and a `-1` offset + CV Invert produces `1 − send` for the dry leg.

```mermaid
flowchart LR
    N1["neg1 (76)<br/>Value = −1"]

    subgraph A["Live wet/dry"]
        FLS["FXLive Send (6)<br/>Value 0.5"]
        WFF1["wetFF (61)"]
        LWG["liveWetG (35)<br/>Multiplier ×2"]
        IL["invLive (36)<br/>CV Invert"]
    end
    FLS --> LWG
    WFF1 --> LWG
    LWG --> DS["drySend (34) level"]
    LWG --> IL
    N1 --> IL
    IL --> LD["Live Dry (33) level"]

    subgraph B["Loop wet/dry"]
        FQS["FXLoop Send (12)<br/>Value 1.0"]
        LFF["loopFxFF (62)"]
        WFF2["wetFF (61)"]
        LPG["loopWetG (41)<br/>Multiplier ×3"]
        IP["invLoop (42)<br/>CV Invert"]
    end
    FQS --> LPG
    LFF --> LPG
    WFF2 --> LPG
    LPG --> LS["loopSend (40) level"]
    LPG --> IP
    N1 --> IP
    IP --> LDR["loopDir (39) level"]
    FQS --> RW["recWet (53) level"]

    subgraph C["Granular wet/dry"]
        GMX["G.Mix (22)"]
        GFF["grnFF (59)"]
        GA["granAmt (45)<br/>Multiplier ×2"]
        IG["invGrn (46)<br/>CV Invert"]
    end
    GMX --> GA
    GFF --> GA
    GA --> GP["granPass (44) level"]
    GA --> IG
    N1 --> IG
    IG --> GD["granDir (43) level"]
```

Delay and Reverb bypass use the same offset trick on their **mix** input:
`mix = D.Mix + dlyFF − 1` (and `R.Mix + revFF − 1`), so mix collapses to fully
dry when the flip-flop is off.

## 3. Stomp control logic

Each stomp is momentary → ADSR (initial-delay acts as the tap/hold timer) →
Out Switch, routing short press to output 1 and long hold to output 2.

```mermaid
flowchart LR
    subgraph SL["Stomp Left — Rec/Dub"]
        S1["Rec/Dub (63)"] --> A1["ADSR (64)<br/>delay 0.44"] --> O1["Out Switch (65)"]
        S1 -->|out_select| O1
        O1 -->|"tap"| RFF["recFF (57)"]
        O1 -->|"tap"| SEQ["Sequencer (66)<br/>3 steps · one-shot"]
        O1 -->|"hold"| PSF["PlayStop (55)"]
        SEQ --> TRG["Trigger (67)"]
    end
    RFF --> REC["LoopL/R · record"]
    RFF --> RIND["recInd (58)"] --> LFXB["L.FX button colour"]
    TRG --> RST["LoopL/R · restart_playback"]
    PSF --> STOP["LoopL/R · stop_play"]

    subgraph SM["Stomp Mid — Frz/Clr"]
        S2["Frz/Clr (68)"] --> A2["tapHold (69)<br/>delay 0.48"] --> O2["Out Switch (70)"]
        S2 -->|out_select| O2
        O2 -->|"tap"| FZF["freezeFF (60)"]
        O2 -->|"hold"| ML["Mid Long (71)<br/>Trigger"]
    end
    FZF --> GFRZ["Grain · freeze"]
    ML --> CLR["LoopL/R · reset (clear)"]
    ML --> SEQ

    subgraph SR["Stomp Right — Wet"]
        S3["Wet (72)"] --> A3["rTapHold (73)<br/>delay 0.48"] --> O3["Out Switch (74)"]
        S3 -->|out_select| O3
        O3 -->|"tap"| WFF["wetFF (61)"]
        O3 -->|"hold"| LFF2["loopFxFF (62)"]
    end
    WFF --> WGATES["wetOut level · liveWetG · loopWetG"]
    LFF2 --> LGATE["loopWetG"]
```

The `record → tap` path is the overdub-bypass hack: `recFF` toggles `record`
while the 3-step one-shot sequencer fires `Trigger (67)` into
`restart_playback`, so the first press records and subsequent presses overdub
without ever hitting a straight-to-overdub state.

## 4. Page 0 grid controls

| Row | Modules |
|---|---|
| Values (row 1) | D.FB, R.Decay, L.Start, G.Pos, G.Density |
| Values (row 2) | FXLive Send, D.Time, R.Low, L.Length, G.Size |
| Values (row 3) | FXLoop Send, D.Depth, R.High, L.Clock, G.Pitch |
| Values (row 4) | Volume, D.Mix, R.Mix, L.Level, G.Mix |
| Buttons | D.On, R.On, L.FX, G.On, L.RevL, L.RevR, G.Freeze, FX On |

UI Buttons are bidirectional: pressing one drives its flip-flop, and the
flip-flop feeds back into the button's `in` at strength ~70 for lighting, with
`OffCol (75) = 0.05` as the dim base colour.
