Aim: Make a connection script between old DB railway_lines and ERA Rinf

>[!warning]
>i need manual transfer of the infrastructure that has been manual added

## Project to Line Of Section
The problem is that in the old db the infrastructure data was not ERA data, but OpenSource DB data. 

Possibilites are:
- mapping between RailwayLine and SectionOfLine
	- das geht z.B. über ein graphisches Mapping, z.B. über geeignete Verschneidungsmethoden von Postgres
		- Problem ist hier die Kontrolle der Verschneidung
	- man könnte es aber auch über ein Routing machen: Jede Section Of Line läuft zwischen Betriebsstellen -> vergleiche welche railway_lines zwischen gleichen Linien verlaufen
	- Wie stelle ich fest, welche Daten überhaupt nicht überschneiden und daher manuell importiert werden müssen? (ich habe in der alten Datenbank händisch viele Daten ergänzt)

>[!idea]
>In diesem Zug könnte auch die Verbindung zwischen RailwayRoute und SectionOfLine hergestellt werden. Das könnte sich in einigen Fällen noch als ganz praktisch erweisen


>[!todo]
>Ich muss die RailwayRoute Attribut manual_added ergänzen in pros-icloud

## Railway Station to OperationPoints
Hier kann ich denke ich recht einfach die Zuordnung machen über railway_stations.db_kuerzel <-> operational_point.op_id

Dabei muss das Kürzel von operational_point.op_id ein wenig angepasst werden (die ersten Buchstaben müssen weg)