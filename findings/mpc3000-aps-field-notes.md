# MPC3000 APS Field Notes

This note records the remaining non-live clarifications for
`mpc3000.aps.v3.ksy` that were resolved directly from Roger Linn's
`MPC file formats.doc`.

Source block:

- `/Users/izmar/projects/VMPC2000XL/reverse_engineer/doc_by_linn/MPC file formats.doc`
- extracted with `textutil -convert txt -stdout ...`
- relevant lines around the APS field table at offsets 196-240

Resolved points:

- `record_live_mix_changes`
  - Roger notes: `0 = yes`, `1 = no`
  - this is the saved `Record Live Changes` flag from the `Mix source / auto mix`
    screen

- top-level `effects_settings`
  - Roger notes: this block is meaningful when `Effects Source = Master`
  - that matches the current choice to keep a top-level effects block in the
    APS layout

- top-level `mixer_settings`
  - Roger notes describe these as the mixer settings used when
    `Stereo Mix Source = Master`
  - the current KSY already models a 64-entry table there, which agrees with
    preserved OS 3.11 APS evidence better than reading the note as a single
    collapsed record

- `effects_settings.delay_msecs_tap{1,2,3}`
  - Roger notes: visible domain `1..1486`

- `effects_settings.effects_on`
  - Roger notes: `1 = on`, `0 = off`

Operational conclusion:

- no further live MPC3000 probing was needed for these APS fields
- the remaining work around MPC3000 APS is now mostly consumer/parity work, not
  binary-structure uncertainty
