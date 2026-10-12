# Digital Lifeline for Home Assistant

Companion integration for the **Digital Lifeline portal**. It pushes critical Home Assistant sensors
(fall detection, alert/panic button, smoke/CO detector, water leak) to the portal **the moment they
trigger**, so family and caregivers are alerted immediately instead of waiting for the portal's
periodic check. It also sends a heartbeat every minute, which gives the green check in the portal.

> **This is an aid, not a certified alarm system.** Do not rely on it as the only safeguard for
> someone's safety.

## Install (HACS)
1. In the portal: **Dashboard → Connection → Lifeline Home Assistant app** → switch it on.
2. In Home Assistant: **HACS → ⋮ → Custom repositories** → add
   `https://github.com/Dreamfox-Media/digital-lifeline-ha` as category **Integration**.
3. Install **Digital Lifeline**, restart Home Assistant.
4. **Settings → Devices & services → Add integration → Digital Lifeline**, paste the webhook URL and
   token shown in the portal.

The portal shows a green check as soon as the integration is connected and the heartbeat arrives.

## What it watches
Detected automatically (you can change this in the integration's **Configure** dialog):

| Portal category | Detected entities |
|---|---|
| Fall detection | `binary_sensor` whose id/name contains `fall`, `val`, `valdetectie` |
| Alert button | `binary_sensor`/`event`/`button` with `panic`, `sos`, `paniek`, `noodknop`, `pendant`… |
| Smoke / CO | `binary_sensor` with device class `smoke` or `carbon_monoxide` |
| Water leak | `binary_sensor` with device class `moisture` |

Sensors that are already mapped in the portal are added automatically.

## Reliability
- Events go into a persistent queue first. If the portal or your internet is down, they are kept (also
  across a Home Assistant restart) and re-sent with back-off. Late events are marked as such.
- Every event has a unique id; the portal ignores duplicates.
- If a critical sensor becomes `unavailable` or its battery is ≤ 10 %, the portal is told so (a silent
  smoke detector is a risk too).
- If the integration stops sending heartbeats, the green check disappears and the portal notifies you.

## Entities, events and services
- `binary_sensor.digital_lifeline_portal_connection` — on while the portal answers (attribute `queued_events`).
- `binary_sensor.digital_lifeline_open_incident` — on while the portal has an open incident.
- Event `digital_lifeline_incident` — fired when the incident list changes (`incidents` in the event data),
  handy for your own automations (siren, lights, TTS). It arrives within about a minute.
- Service `digital_lifeline.send_test_event` — sends a flagged test through the full path (no incident, nobody notified).

## Privacy
Only entity id, friendly name, state and timestamp of the watched critical entities are sent, plus
the integration and Home Assistant version. Nothing else from your installation leaves your network.

---

# Nederlands

Aanvulling op het **Digital Lifeline-portaal**. Stuurt kritieke sensoren (valdetectie,
waarschuwings-/paniekknop, rook/CO, waterlek) **direct** naar het portaal en stuurt elke minuut een
levensteken, waarmee het portaal een groen vinkje toont.

> **Dit is een hulpmiddel, geen gecertificeerd alarmsysteem.**

**Installeren:** zet de app aan in het portaal (Dashboard → Verbinding), voeg in HACS de repository
`https://github.com/Dreamfox-Media/digital-lifeline-ha` toe als *Integratie*, installeer, herstart
Home Assistant, voeg de integratie *Digital Lifeline* toe en plak de webhook-URL en het token uit het portaal.

Meldingen worden eerst in een duurzame wachtrij gezet en opnieuw verstuurd als het portaal of internet
tijdelijk weg is (ook na een herstart). Het portaal negeert dubbele meldingen.
