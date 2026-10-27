<p align="center">
  <img src="https://raw.githubusercontent.com/Dreamfox-Media/digital-lifeline-ha/main/docs/images/hero.jpg" alt="An older woman reading a book on her sofa at home" width="100%">
</p>

<p align="center">
  <img src="https://raw.githubusercontent.com/Dreamfox-Media/digital-lifeline-ha/main/docs/images/logo.png" alt="Digital Lifeline logo: a house with a heartbeat" width="120">
</p>

<h1 align="center">Digital Lifeline for Home Assistant</h1>

<p align="center">
  <b>Let family and caregivers know within seconds when something is wrong at home.</b><br>
  <a href="#english">English</a> · <a href="#nederlands">Nederlands</a>
</p>

<p align="center">
  <a href="https://ha.digilifeline.com"><b>ha.digilifeline.com</b></a> (English) ·
  <a href="https://ha.digilifeline.nl"><b>ha.digilifeline.nl</b></a> (Nederlands)
</p>

<p align="center">
  <a href="https://my.digilifeline.com"><img alt="Portal" src="https://img.shields.io/badge/portal-my.digilifeline.com-1d6fa5"></a>
  <a href="https://github.com/Dreamfox-Media/digital-lifeline-ha/releases"><img alt="Release" src="https://img.shields.io/github/v/release/Dreamfox-Media/digital-lifeline-ha"></a>
  <a href="https://hacs.xyz"><img alt="HACS custom repository" src="https://img.shields.io/badge/HACS-custom%20repository-41bdf5"></a>
  <a href="LICENSE"><img alt="License MIT" src="https://img.shields.io/github/license/Dreamfox-Media/digital-lifeline-ha"></a>
</p>

---

<a id="english"></a>

# English

## What is this for?

**Digital Lifeline** helps people who live alone, often older relatives, stay independent while the people
who care about them can stay at ease. Sensors in the home (a fall detector, an alert button, a smoke
detector) are watched by **Home Assistant**. This integration connects Home Assistant to the
**Digital Lifeline portal**, so that when one of those sensors triggers, **family and caregivers are
notified immediately**, on their phone, by e-mail and by SMS as a backup.

Without this integration the portal checks your Home Assistant every few minutes. That is fine for
everyday status, but a short alarm can already be over by then, and nothing arrives at all when the
portal cannot reach your Home Assistant. This integration closes that gap: **your Home Assistant
pushes the alarm itself, the moment it happens.**

<table>
  <tr>
    <td width="50%"><img src="https://raw.githubusercontent.com/Dreamfox-Media/digital-lifeline-ha/main/docs/images/sensors.jpg" alt="Small white home sensors: motion sensor, door sensors and an alert button"></td>
    <td width="50%"><img src="https://raw.githubusercontent.com/Dreamfox-Media/digital-lifeline-ha/main/docs/images/family-app.jpg" alt="A relative looking at the Digital Lifeline app on their phone"></td>
  </tr>
  <tr>
    <td align="center"><b>At home:</b> the sensors you already have in Home Assistant</td>
    <td align="center"><b>Elsewhere:</b> family and caregivers see the status and get alerted</td>
  </tr>
</table>

Learn more about the project, or sign up to test it, at **[ha.digilifeline.com](https://ha.digilifeline.com)**.

> **This is an aid, not a certified alarm system.** Do not rely on it as the only safeguard for
> someone's safety.

## How it works

<p align="center">
  <img src="https://raw.githubusercontent.com/Dreamfox-Media/digital-lifeline-ha/main/docs/images/how-it-works.svg" alt="Sensors at home trigger the Digital Lifeline integration in Home Assistant, which pushes the alert to the Lifeline portal, which notifies family and caregivers" width="100%">
</p>

1. A critical sensor in Home Assistant triggers (for example fall detection).
2. The integration puts the event in a **persistent queue** and sends it to the portal straight away.
3. The portal removes duplicates, opens an **incident** and runs its emergency chain: app notification,
   e-mail and SMS backup to the people you chose.
4. Every minute the integration sends a **heartbeat**. As long as it arrives, the portal shows a
   **green check**. If it stops, the check disappears and you are told that the connection is down.

You can also see the open incident from inside Home Assistant (see [Entities](#entities-events-and-services)),
for example to switch on a siren or lights.

## What it watches

Detected automatically (you can change this in the integration's **Configure** dialog):

| Portal category | Detected entities |
|---|---|
| Fall detection | `binary_sensor` whose id/name contains `fall`, `val`, `valdetectie` |
| Alert button | `binary_sensor`/`event`/`button` with `panic`, `sos`, `paniek`, `noodknop`, `pendant`… |
| Smoke / CO | `binary_sensor` with device class `smoke` or `carbon_monoxide` |
| Water leak | `binary_sensor` with device class `moisture` |

Sensors that are already mapped in the portal are added automatically.

## Install (HACS)

You need a Digital Lifeline account. Not a user yet? See [ha.digilifeline.com](https://ha.digilifeline.com).

1. In the portal: **Dashboard → Connection → Lifeline Home Assistant app** → switch it on.
2. In Home Assistant: **HACS → ⋮ → Custom repositories** → add
   `https://github.com/Dreamfox-Media/digital-lifeline-ha` as category **Integration**.
3. Install **Digital Lifeline**, restart Home Assistant.
4. **Settings → Devices & services → Add integration → Digital Lifeline**, paste the webhook URL and
   token shown in the portal.

The portal shows a green check as soon as the integration is connected and the heartbeat arrives.
Use the service `digital_lifeline.send_test_event` to send a flagged test through the full path (no
incident is created and nobody is notified).

## Reliability

- Events go into a persistent queue first. If the portal or your internet is down, they are kept (also
  across a Home Assistant restart) and re-sent with back-off. Late events are marked as such.
- Every event has a unique id; the portal ignores duplicates.
- If a critical sensor becomes `unavailable` or its battery is ≤ 10 %, the portal is told so (a silent
  smoke detector is a risk too).
- If the integration stops sending heartbeats, the green check disappears and the portal notifies you.

## Entities, events and services

- `binary_sensor.digital_lifeline_portal_connection`: on while the portal answers (attribute `queued_events`).
- `binary_sensor.digital_lifeline_open_incident`: on while the portal has an open incident.
- Event `digital_lifeline_incident`: fired when the incident list changes (`incidents` in the event data),
  handy for your own automations (siren, lights, TTS). It arrives within about a minute.
- Service `digital_lifeline.send_test_event`: sends a flagged test through the full path (no incident, nobody notified).

## Privacy

Only entity id, friendly name, state and timestamp of the watched critical entities are sent, plus
the integration and Home Assistant version. Nothing else from your installation leaves your network.

## Links

- Project and sign-up: [ha.digilifeline.com](https://ha.digilifeline.com)
- Portal: [my.digilifeline.com](https://my.digilifeline.com)
- Questions or problems: [open an issue](https://github.com/Dreamfox-Media/digital-lifeline-ha/issues)
- Made with ❤️ by [smartrevolutions.nl](https://smartrevolutions.nl)

---

<a id="nederlands"></a>

# Nederlands

## Waar is dit voor?

**Digital Lifeline** helpt mensen die alleen wonen, vaak oudere familieleden, zelfstandig te blijven,
terwijl de mensen om hen heen gerust kunnen zijn. Sensoren in huis (een valdetector, een noodknop, een
rookmelder) worden bewaakt door **Home Assistant**. Deze integratie verbindt Home Assistant met het
**Digital Lifeline-portaal**: gaat zo'n sensor af, dan krijgen **familie en mantelzorgers direct een
melding**, op hun telefoon, per e-mail en als back-up per sms.

Zonder deze integratie kijkt het portaal om de paar minuten in je Home Assistant. Dat is prima voor de
gewone status, maar een korte melding kan dan al voorbij zijn, en als het portaal je Home Assistant niet
kan bereiken, komt er helemaal niets door. Deze integratie dicht dat gat: **je Home Assistant stuurt het
alarm zelf, op het moment dat het gebeurt.**

<table>
  <tr>
    <td width="50%"><img src="https://raw.githubusercontent.com/Dreamfox-Media/digital-lifeline-ha/main/docs/images/sensors.jpg" alt="Kleine witte sensoren: bewegingsmelder, deursensoren en een noodknop"></td>
    <td width="50%"><img src="https://raw.githubusercontent.com/Dreamfox-Media/digital-lifeline-ha/main/docs/images/family-app.jpg" alt="Een familielid kijkt op de telefoon naar de Digital Lifeline-app"></td>
  </tr>
  <tr>
    <td align="center"><b>Thuis:</b> de sensoren die je al in Home Assistant hebt</td>
    <td align="center"><b>Elders:</b> familie en mantelzorgers zien de status en krijgen een melding</td>
  </tr>
</table>

Meer over het project, of aanmelden als tester: **[ha.digilifeline.nl](https://ha.digilifeline.nl)**.

> **Dit is een hulpmiddel, geen gecertificeerd alarmsysteem.** Vertrouw er niet op als enige
> bescherming van iemands veiligheid.

## Hoe werkt het?

<p align="center">
  <img src="https://raw.githubusercontent.com/Dreamfox-Media/digital-lifeline-ha/main/docs/images/how-it-works.svg" alt="Sensoren thuis activeren de Digital Lifeline-integratie in Home Assistant, die de melding doorstuurt naar het Lifeline-portaal, dat familie en mantelzorgers waarschuwt" width="100%">
</p>

1. Een kritieke sensor in Home Assistant gaat af (bijvoorbeeld valdetectie).
2. De integratie zet de melding in een **duurzame wachtrij** en verstuurt hem meteen naar het portaal.
3. Het portaal filtert dubbele meldingen, opent een **incident** en start de noodketen: pushmelding in de
   app, e-mail en sms als back-up, naar de mensen die jij hebt gekozen.
4. Elke minuut stuurt de integratie een **levensteken**. Zolang dat aankomt, toont het portaal een
   **groen vinkje**. Valt het weg, dan verdwijnt het vinkje en krijg je bericht dat de verbinding weg is.

Je kunt het open incident ook in Home Assistant gebruiken, bijvoorbeeld om een sirene of verlichting aan
te zetten (zie [Entiteiten](#entiteiten-events-en-services)).

## Wat wordt bewaakt?

Automatisch herkend (aan te passen via **Configureren** bij de integratie):

| Categorie in het portaal | Herkende entiteiten |
|---|---|
| Valdetectie | `binary_sensor` met `fall`, `val`, `valdetectie` in id/naam |
| Noodknop | `binary_sensor`/`event`/`button` met `panic`, `sos`, `paniek`, `noodknop`, `pendant`… |
| Rook / CO | `binary_sensor` met device class `smoke` of `carbon_monoxide` |
| Waterlek | `binary_sensor` met device class `moisture` |

Sensoren die al in het portaal zijn gekoppeld, worden automatisch toegevoegd.

## Installeren (HACS)

Je hebt een Digital Lifeline-account nodig. Nog geen gebruiker? Kijk op [ha.digilifeline.nl](https://ha.digilifeline.nl).

1. In het portaal: **Dashboard → Verbinding → Lifeline Home Assistant-app** → zet de app aan.
2. In Home Assistant: **HACS → ⋮ → Aangepaste repositories** → voeg
   `https://github.com/Dreamfox-Media/digital-lifeline-ha` toe als categorie **Integratie**.
3. Installeer **Digital Lifeline** en herstart Home Assistant.
4. **Instellingen → Apparaten & services → Integratie toevoegen → Digital Lifeline**, plak de webhook-URL
   en het token uit het portaal.

Het portaal toont een groen vinkje zodra de integratie verbonden is en het levensteken aankomt. Met de
service `digital_lifeline.send_test_event` stuur je een gemarkeerde test door de hele keten (er komt geen
incident en niemand krijgt een melding).

## Betrouwbaarheid

- Meldingen gaan eerst in een duurzame wachtrij. Is het portaal of je internet tijdelijk weg, dan blijven
  ze bewaard (ook na een herstart van Home Assistant) en worden ze opnieuw verstuurd. Late meldingen
  worden als zodanig gemarkeerd.
- Elke melding heeft een uniek id; het portaal negeert dubbele meldingen.
- Wordt een kritieke sensor `unavailable` of is de batterij ≤ 10 %, dan meldt de integratie dat aan het
  portaal (een stille rookmelder is ook een risico).
- Stopt het levensteken, dan verdwijnt het groene vinkje en krijg je bericht van het portaal.

## Entiteiten, events en services

- `binary_sensor.digital_lifeline_portal_connection`: aan zolang het portaal antwoordt (attribuut `queued_events`).
- `binary_sensor.digital_lifeline_open_incident`: aan zolang er een open incident is.
- Event `digital_lifeline_incident`: wordt afgevuurd als de incidentenlijst wijzigt (`incidents` in de
  eventdata), handig voor eigen automatiseringen (sirene, lampen, TTS). Komt binnen ongeveer een minuut aan.
- Service `digital_lifeline.send_test_event`: stuurt een gemarkeerde test door de hele keten.

## Privacy

Alleen entity-id, vriendelijke naam, status en tijdstip van de bewaakte kritieke entiteiten worden
verstuurd, plus de versie van de integratie en van Home Assistant. Niets anders uit je installatie
verlaat je netwerk.

## Links

- Project en aanmelden: [ha.digilifeline.nl](https://ha.digilifeline.nl)
- Portaal: [mijn.digitallifeline.nl](https://mijn.digitallifeline.nl)
- Vragen of problemen: [maak een issue aan](https://github.com/Dreamfox-Media/digital-lifeline-ha/issues)
- Met ❤️ gemaakt door [smartrevolutions.nl](https://smartrevolutions.nl)

---

<p align="center"><sub>Made with ❤️ by <a href="https://smartrevolutions.nl">smartrevolutions.nl</a> · © Dreamfox Media · MIT License</sub></p>
