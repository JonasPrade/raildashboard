## Implementation
The aim is to generate the structure of the table automated from the 

### Tables
#### implemented
- OperationalPoint: contains OperationalPoints as in RINF (era:OperationalPoint)
- SectionOfLine: contains SectionsOfLine as in RINF (era:SectionOfLine)
- SOLTrack: contains SOLTracks as in RINF (era:Track)
- SOLTrackParameter: contains SOLTrackParameters as in RINF (era:TrackParameter)
#### not implemented
- PlatformEdge: passenger platforms at OPs (era:PlatformEdge)
- Tunnel: tunnels along a SectionOfLine (era:Tunnel)
- Bridge: bridges along a SectionOfLine (era:Bridge)
- Siding: auxiliary tracks linked to OPs (era:Siding)
- SpecialArea: restricted or functional areas (era:SpecialArea)
- RailwayLocation: position along track in kilometers (era:RailwayLocation)
### Import of RINF Data

This process describes how to download the RINF data and import it into the local database.

**Step 1: Configuration**
- In `config.py`, set the necessary configurations.
- In the `.env` file, provide the required API information for the ERA database.

**Step 2: Download RINF XML Files**
- Run the `download_xml.py` script to fetch the latest RINF data for all member states. The files will be saved in the directory specified in the config (e.g., `output/xml_countries`).
  ```bash
  python scripts/import_rinf_data/download_xml.py
  ```

**Step 3: Import Data into Database**
- Use the `import_xml.py` script to parse a specific country's XML file and load the data into the database.

- **Command:**
  ```bash
  python scripts/import_rinf_data/import_xml.py <country_code> [--clear]
  ```

- **Arguments:**
  - `<country_code>`: **(Required)** The two-letter country code for which to import data (e.g., `DE`).
  - `--clear`: **(Optional)** If specified, all existing data in the relevant database tables (`OperationalPoint`, `SectionOfLine`, etc.) will be deleted before the new data is imported.

- **Examples:**
  - To import data for Germany without clearing existing data:
    ```bash
    python scripts/import_rinf_data/import_xml.py DE
    ```
  - To clear all previous data and import the data for Austria:
    ```bash
    python scripts/import_rinf_data/import_xml.py AT --clear
    ```

### Structure of XML Schema
https://data-interop.era.europa.eu/vocabulary



