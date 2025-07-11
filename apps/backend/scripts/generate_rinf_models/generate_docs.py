def generate_markdown_docs(class_map: dict, output_path):
    lines = ["# ERA RINF Ontology – Extracted Classes", ""]

    for class_name, meta in class_map.items():
        lines.append(f"## {class_name}")
        lines.append(f"- URI: `{meta['uri']}`")
        if 'label' in meta and meta['label']:
            lines.append(f"- Label: {meta['label']}")
        if 'comment' in meta and meta['comment']:
            lines.append(f"- Comment: {meta['comment']}")
        if 'superclass' in meta and meta['superclass']:
            lines.append(f"- Superclass: `{meta['superclass']}`")
        if 'properties' in meta and meta['properties']:
            lines.append("")
            lines.append("- Properties")
            for name, datatype in meta['properties']:
                lines.append(f"  - `{name}`: `{datatype}`")
        lines.append("")

    output_path.write_text("\n".join(lines), encoding="utf-8")
