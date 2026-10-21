# TR-808 NGSpice Simulation

A standalone, device-level [NGSpice](https://ngspice.sourceforge.io/) simulation of a Roland [TR-808](https://en.wikipedia.org/wiki/Roland_TR-808) drum machine, built from the [*Yocto V2.0*](https://github.com/e-licktronic/Yocto-V2.0) TR-808-clone schematic (v2.007) (device models taken from verified datasheets) and calibrated against recordings of the target hardware.

This package is intentionally minimal: just the circuit and what you need to run it. [`tr808_full.cir`](tr808_full.cir) is fully **self-contained** — every transistor / diode / JFET model and subcircuit is defined inline, so there are **no external `.include` / `.lib` files** and no separate model files required.

## Requirements
- **[NGSpice](https://ngspice.sourceforge.io/)** version **47** (any recent release works; developed and tested with the NGSpice 47 Windows build). → [Download](https://ngspice.sourceforge.io/download.html) · [Documentation](https://ngspice.sourceforge.io/docs.html) · [User's manual v47 (PDF)](https://ngspice.sourceforge.io/docs/ngspice-47-manual.pdf)
- No other dependencies — just a SPICE simulator.

## Running it
```bash
ngspice tr808_full.cir          # or: ngspice_con -b tr808_full.cir
```
The netlist runs a **4 s transient** (`uic` initial conditions, Gear integration, 20 µs maximum step; the solver settings are set in the file because the defaults can stop with "Timestep too small") and writes the node voltages listed in the `wrdata` line to `tr808_full_nodes.txt`. This is a heavy run: measured with NGSpice 47 on a 24-core Windows PC (NGSpice uses one core per run, other jobs were running at the same time), it took about 70 minutes and wrote a 4.8 GB `tr808_full_nodes.txt` (14.8 million rows). For quick checks, copy the file and shorten the `.tran` line.

Convert the dump to audio with [`scripts/nodes_to_wav.py`](scripts/nodes_to_wav.py) (needs only Python + numpy): `python scripts/nodes_to_wav.py --node sd_out` writes `wav/sd_out.wav` (48 kHz mono; without `--node` every dumped node).

Main output nodes: `cy_out`, `bd_out`, `sd_out`, `oh_out`, `ch_out`, IO buses `busr` / `busl`, master outputs `u1a_out` / `u1b_out`.

## Example samples
[`samples/`](samples) holds five single hits rendered from this netlist with the default knob positions (all other voices untriggered, trigger at 50 ms, `.tran` stopped after the decay): `kick.wav`, `snare.wav`, `closed_hat.wav`, `open_hat.wav`, `cymbal.wav`. They are the voice output nodes (`bd_out`, `sd_out`, `ch_out`, `oh_out`, `cy_out`), mono, 48 kHz, 16 bit, converted with `scripts/nodes_to_wav.py --start 0.04` (the first 40 ms, the power-up transient of the `uic` start, are dropped) and each normalized to −1 dBFS on its own, so the relative levels of the files are not preserved. Each hit took 20–70 minutes to simulate.

## Circuit contents
One integrated circuit, all voices sharing the same supply rails, IO buses and master output stage (as on the real board):

| Voice | Trigger `.param` | Pot / knob `.param` |
|---|---|---|
| Bass drum (Kick) | `trig_bd_amp` | `bd_vr4`, `bd_vr5`, `bd_vr6` |
| Snare | `trig_sd_amp` | `sd_vr7`, `sd_vr8`, `sd_vr9` |
| Tom / Conga Low · Mid · Hi | `trig_lt_amp` / `trig_mt_amp` / `trig_ht_amp` | `lt_vr10/11`, `mt_vr12/13`, `ht_vr14/15`, `*_sw` |
| Rim Shot / Claves | `trig_rm_amp` | `rm_vr16`, `rm_sw` |
| Hand Clap / Maracas | `trig_hc_amp` | `hc_vr17`, `hc_tm3`, `hc_sw` |
| Cowbell | `trig_cb_amp` | `cb_vr5` |
| PC-2 | `trig_pc2_amp` | `pc2_vr1/2/3/18/19/20`, `pc2_tm5`, `pc2_sw2/3` |
| Hi-Hat Open / Closed | `trig_oh_amp` / `trig_ch_amp` | — |
| Cymbal / Ride | `trig_cy_amp` | — |
| Master output stage | — | `vr28` |

Plus per-voice trigger timing (`<voice>_tdelay`, `<voice>_twidth`). A voice is armed when its `trig_*_amp` is non-zero (default: Kick / Snare / Cymbal armed, the rest `0`). Pot values are wiper fractions in `0..1`.

## Verification status

**Netlist vs. source** (Yocto v2.007 schematic and routed board, checked by script; deviations in every row: 0)

| Section | Checked |
|---|---|
| Cymbal / Ride (shared oscillator bank) | 136 components, 90 nets; all 136 components in the part inventory marked verified, 0 open |
| Hi-Hat (OH/CH) | 85 of 85 components present, 65 of 65 R/C values; designators identical to the Roland service plan |
| Bass drum | 31 nets vs. board, 51 elements, 36 R/C values |
| Snare + noise | 52 nets, 76 elements, 46 R/C values |
| Toms / Congas | 108 nets, 164 elements (13 switch contacts), 133 values |
| Rim Shot / Claves | 44 nets, 71 elements, 62 values |
| Cowbell | 42 components, 94 pins, 34 nets |
| PC-2 | 84 components, 203 pins, 62 nets, 67 values, 19 models, 6 switches |

**Device models**

| Model | Source | Check |
|---|---|---|
| 2SC945 (`Q2SC945`) | NEC D17117 | 7 of 7 datasheet test cases, 0.0–3.3 % deviation |
| 2SA733 (`Q2SA733`) | Renesas/NEC D10868 | hFE / VBE / Cob < 2 %; VCE(sat) 3–8 %, VBE(sat) 5–6 % |
| 1N4148 (`D1N4148`) | Nexperia SPICE model, verbatim | VF, IR, Cd, trr, Vfr |
| µPC4558 (`UPC4558_V3`) | NEC G10518 | 9 datasheet parameters, 0–0.36 %; output resistance is a placeholder (no datasheet value) |
| CD4584 (`SCHMITT4584`) | MC14584B threshold table at VDD = 5 V | hysteresis 0.12·VDD matches the tabulated VH |
| 2SC828 base-emitter breakdown (Q35) | V(BR)EBO = 7 V @ 10 µA, two independent sources | breakdown voltage only; noise amplitude is a placeholder |
| BA6110 OTA | ROHM BA6110FS | Fig. 8 within 1.5 dB; model gm 9.62 mS vs. 4.8 / 8 / 12 mS (min / typ / max) in the table |
| AN6912 comparator | datasheet | sensitivity tests on offset and bias current |
| 2SK30A (`J2SK30`) | Toshiba datasheet, published rank-Y model | within the rank-Y bounds; Vto of the individual part is not determined by the datasheet |

**Calibration against Yocto2 recordings** (effective values within the specified range, not measured part values): Toms/Congas (1N34 IS 4e-7, capacitor tan δ 0.3 %), Rim Shot/Claves (tan δ 0.5 %, Claves tolerance instance C117/C119/R308/R312/R313), Snare (bridged-T capacitors 27n/6n8), PC-2 (JFET Vto −0.54 V, CPC27 3.32 µ), Cowbell, Hi-Hat and Cymbal. The Kick is left as is (frequency 5 % high against the recording).

## Known limitations
- **Un-modeled / placeholder blocks** (see the header of [`tr808_full.cir`](tr808_full.cir)): `Q82`/`Q83` (2SC2878 — no verified model), the `Q79` bias network, and the headphone / left-right output path behind them.
- The snare noise **amplitude** is an explicit placeholder: the avalanche/microplasma mechanism is modeled, but its amplitude is not hardware-derived.
- The deck is calibrated to target-hardware recordings; passive parts are idealized (no tan-delta / ESR / tolerance) unless a measured effect justified it.

## References
- **Yocto V2.0** — the TR-808 clone whose schematic this simulation is based on (source build plan / Eagle net): [github.com/e-licktronic/Yocto-V2.0](https://github.com/e-licktronic/Yocto-V2.0)
- **NGSpice** — [project site](https://ngspice.sourceforge.io/) · [downloads](https://ngspice.sourceforge.io/download.html) · [documentation](https://ngspice.sourceforge.io/docs.html) · [user's manual v47 (PDF)](https://ngspice.sourceforge.io/docs/ngspice-47-manual.pdf) · [source on GitHub](https://github.com/ngspice/ngspice)
- **Roland TR-808** — the instrument being simulated: [overview](https://en.wikipedia.org/wiki/Roland_TR-808)

## License
[MIT](LICENSE).
