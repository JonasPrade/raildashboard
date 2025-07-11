def generate_sqlalchemy(class_map: dict, output_path):
    lines = [
        "from sqlalchemy import Column, Integer, String, Float, Boolean, Date",
        "from dashboard_backend.db.base import Base",
        "",
    ]

    for class_name, meta in class_map.items():
        lines.append(f"class {class_name}(Base):")
        lines.append(f"    __tablename__ = '{class_name.lower()}'")
        lines.append("    id = Column(Integer, primary_key=True)")

        for prop, range_uri in meta["properties"]:
            col_type = "String"
            if range_uri:
                if "float" in range_uri:
                    col_type = "Float"
                elif "boolean" in range_uri:
                    col_type = "Boolean"
                elif "date" in range_uri:
                    col_type = "Date"
                elif "integer" in range_uri:
                    col_type = "Integer"

            lines.append(f"    {prop.lower()} = Column({col_type})")

        lines.append("")
    output_path.write_text("\n".join(lines), encoding="utf-8")
