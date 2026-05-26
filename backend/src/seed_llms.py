import json
import os
import pathlib
from src.services.db_service import DatabaseService, LLMModel

def seed_llms():
    print("Seeding LLMs from llms.json to the database...")
    db_service = DatabaseService()
    
    try:
        # Check if llms table already has entries
        existing_count = db_service.db.query(LLMModel).count()
        if existing_count > 0:
            print(f"Database already has {existing_count} LLM entries. Skipping seeding.")
            return
            
        # Read llms.json
        # Check standard relative path first, then absolute container path
        catalog_path = pathlib.Path(__file__).parent / "llms.json"
        if not catalog_path.exists():
            catalog_path = pathlib.Path("/app/src/llms.json")
            
        if not catalog_path.exists():
            print("Error: llms.json not found.")
            return

        with open(catalog_path, "r", encoding="utf-8") as f:
            catalog = json.load(f)

        for item in catalog:
            llm = LLMModel(
                id=item["id"],
                provider=item["provider"],
                model_name=item["model_name"],
                display_name=item["display_name"],
                daily_token_limit=item.get("daily_token_limit", 1000000),
                plans_supported=item.get("plans_supported", ["free", "paid"]),
                supports_tool_calling=item.get("supports_tool_calling", True),
                supports_structured_output=item.get("supports_structured_output", True)
            )
            db_service.db.add(llm)
            
        db_service.db.commit()
        print(f"Successfully seeded {len(catalog)} LLMs into the database.")
    except Exception as e:
        print(f"Error while seeding LLM catalog: {e}")
        db_service.db.rollback()
    finally:
        db_service.db.close()

if __name__ == "__main__":
    seed_llms()
