- [ ] project data
	- [x] project_groups
	- [x] projectcontent_to_group
	- [ ] projectcontent_to_lines
		- die werde ich so 
	- [ ] projectcontent_to_railwaystations
	- [x] project_content
		- [x] import script for project content
		- this is the new `project` table
		- save the id as `id_old`
		- [x] the superior project id has to be changed to the new id
			- save old id
			- after commit reconstruct to new id
		- the bvwp data gets ignored -> will be implemented later
		- [x] some project_id are double?? -> correct that


## ProjectToLines and ProjectToStation
[[Connection between DB Open Data and ERA Rinf]]

new idea for mapping:
- i have an geojson representation

## Export of ProjectContent
The query for the selection of the Project in the old db is

```sql
WITH RECURSIVE recursive_projects AS (  
  -- Starte mit allen Projekten, die eine projekt_number haben oder in projectcontent_to_group vorkommen  
  SELECT pc.*  
  FROM projects_contents AS pc  
  WHERE pc.project_number IS NOT NULL  
  
  UNION  
  SELECT pc.*  
  FROM projects_contents AS pc  
  JOIN projectcontent_to_group AS pcg ON pc.id = pcg.projectcontent_id  
  
  UNION  
  
  -- Füge alle Subprojekte hinzu, deren superior_project_content_id in der Liste ist  
  SELECT pc_sub.*  
  FROM projects_contents AS pc_sub  
  JOIN recursive_projects AS rp ON pc_sub.superior_project_content_id = rp.id  
)  
SELECT DISTINCT *  
FROM recursive_projects;

```