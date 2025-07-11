from generate_rinf_models.config import TTL_FILE, OUTPUT_DIR, STUB_FILE, DOC_FILE
from generate_rinf_models.extract_properties import extract_all_properties
from generate_rinf_models.generate_sqlalchemy_models import generate_sqlalchemy
from generate_rinf_models.generate_docs import generate_markdown_docs

def main():
    print("📦 Parsing ontology and extracting classes...")
    class_data = extract_all_properties(TTL_FILE)

    print("🧱 Generating SQLAlchemy stubs...")
    generate_sqlalchemy(class_data, STUB_FILE)

    print("📝 Creating Markdown documentation...")
    generate_markdown_docs(class_data, DOC_FILE)

    print("✅ All files generated:")
    print(f"   • SQLAlchemy models → {STUB_FILE}")
    print(f"   • Documentation     → {DOC_FILE}")

if __name__ == "__main__":
    main()