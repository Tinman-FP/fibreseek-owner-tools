# FibreSeeker 3 troubleshooting field guide

This guide collects useful, reproducible diagnostic methods learned while
commissioning one FibreSeeker 3. It is deliberately not a defect list. A
symptom on one machine or software release should not be assumed to affect
another machine.

Start with observation and log collection. Change one thing at a time, retain
the original files, and record the installed firmware version.

## Identify the failing layer

The FibreSeeker combines several layers that can report similar-looking
failures:

| Layer | Useful evidence |
| --- | --- |
| Network | Printer IP, browser reachability, TCP connection result |
| Moonraker/API | `/server/info`, HTTP status, request timestamp |
| Klipper | `klippy.log`, `print_stats`, homed axes, heater targets |
| Touchscreen | `anisotouch` logs and the exact on-screen message |
| Tool selection | Active extruder, physical nozzle, first `T0`/`T1` commands |
| Contact probing | Raw repeated probe values at the same XY and temperature |
| Slicer/G-code | Submitted filename, checksum, tool and heater commands |

A screenshot alone can be ambiguous. Pair it with the timestamp and a support
bundle whenever possible.

## Read-only status checks

Moonraker is available through the printer web server on tested stock software.
Replace the sample address with the printer's address:

```sh
curl -fsS http://192.168.50.113/server/info | python3 -m json.tool
curl -fsS http://192.168.50.113/printer/info | python3 -m json.tool
curl -fsS http://192.168.50.113/machine/system_info | python3 -m json.tool
```

Capture useful live state without sending printer commands:

```sh
curl -fsS \
  'http://192.168.50.113/printer/objects/query?print_stats&virtual_sdcard&toolhead&heater_bed&extruder&extruder1&heater_generic%20chamber&bed_mesh&probe' \
  | python3 -m json.tool
```

Or use the repository collector:

```sh
python3 scripts/collect_diagnostics.py 192.168.50.113
```

The collector does not home, heat, move, calibrate, print, restart services, or
write configuration.

## Useful log locations

On the tested software, useful files under `~/printer_data/logs/` included:

- `klippy.log`: Klipper configuration, G-code execution, probe results, and
  shutdown reasons.
- `moonraker.log`: HTTP/API requests, component startup, update status, and
  print-start responses.
- `print_logs/anisotouch_YYYY-MM-DD.log`: touchscreen and OEM workflow events.
- `fibreseek_install.log`: firmware installation activity.
- `fibretouch-ai.log`: AI service activity.
- `blackbox.log`: compact event records.
- `fibretouch_remote_logs/moonraker_broker_bridge.log`: remote-service bridge
  activity.

File availability and names can change by firmware release. The collector first
asks Moonraker for the actual log inventory and downloads only recognized
current logs plus the newest touchscreen log.

## Tool selection and probing

On the tested machine:

- Physical `T0` was the left composite head.
- Physical `T1` was the right plastic FFF nozzle.
- A full stock `G28` selected `T0` for Z contact probing even before a T1-only
  plastic print.

That distinction matters. A T1-only G-code file can still depend on the
condition, seating, and calibration of T0 during homing and bed measurement.
Before diagnosing a probing failure, record both the intended printing tool and
the physical tool used for contact probing.

After changing either nozzle, use the manufacturer's nozzle-offset and bed
calibration sequence before judging print quality or Z accuracy.

## Probe repeatability

An accepted home or mesh does not by itself prove repeatability. To separate
bed shape from contact-sensing variation, compare multiple touches at exactly
the same XY coordinate.

Record:

- printer and firmware version;
- physical probing tool;
- nozzle condition and whether it was recently changed;
- bed, nozzle, and chamber temperatures;
- XY coordinate;
- every raw reading, range, and standard deviation; and
- configured sample tolerance.

Run the same comparison cold and at normal operating temperature. A test that
passes cold but varies hot is useful evidence for checking nozzle seating,
toolhead rigidity, sensor mounting, connectors, and temperature-dependent
signal behavior. Do not hide poor raw repeatability by increasing a tolerance
or relying only on a filtered mesh statistic.

## Print start returns HTTP 504

During testing, a print-start request sometimes reached the printer and entered
preparation even though nginx later returned HTTP 504 to the client. Treat a
timeout as an ambiguous result:

1. Do not immediately submit the same start request again.
2. Query `print_stats` and `virtual_sdcard`.
3. Compare the active filename with the requested filename.
4. If the matching job is `preprinting`, `printing`, or `paused`, treat the
   original request as accepted.
5. If the printer is idle or the filename differs, preserve the HTTP response
   and logs before retrying.

This avoids duplicate or conflicting starts while still exposing a genuine
failure when no matching job exists.

## Cancel during preparation

Some preparation macros are long-running. A normal cancel request may not be
processed immediately while one is executing. Avoid sending repeated cancel or
start commands. Record the request time, watch live state, and use the printer's
documented controls if immediate intervention is required.

## Door and other preflight messages

When a start is rejected before heating or motion, capture:

- the HTTP status and response body;
- the exact touchscreen message;
- the corresponding sensor object state; and
- Moonraker and Klipper logs covering the same timestamp.

This helps distinguish a physical sensor state, a touchscreen workflow check,
a Moonraker preflight decision, and a Klipper runtime sensor action. Repair and
verify the physical interlock rather than treating a software bypass as the
finished solution.

## Firmware version sources

The update screen, package filename, `/server/info`, and `/printer/info` may not
all expose the same version fields. Record the touchscreen's installed version,
the exact package filename, the update timestamp, and the status returned by the
updater. Avoid inferring the installed release from only one missing or `?`
field.

## G-code parser isolation

If a command works alone but fails when followed by an inline `; comment`, save
both lines and the exact log error. Reproduce with a comment-free command rather
than assuming a heater or motion failure. This produces a small, useful parser
case for the manufacturer while keeping the machine-state diagnosis separate.

## Before sharing diagnostics

The collector redacts common IP, MAC, email, hostname, machine-ID, and serial
fields unless `--include-identifiers` is supplied. Redaction is best effort.
Always inspect the generated directory and ZIP before posting them publicly.

For manufacturer support, identifiers may be necessary; use
`--include-identifiers` only when the resulting bundle will be sent privately.
