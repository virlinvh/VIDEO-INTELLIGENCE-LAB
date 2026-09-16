import argparse
import sys
from backend.app.transcription.registry import registry
from backend.app.transcription.models import ModelStatus

def main():
    parser = argparse.ArgumentParser(description="Video Intelligence Lab Model Management CLI")
    subparsers = parser.add_subparsers(dest="command", help="Model management commands")

    # models list
    list_parser = subparsers.add_parser("list", help="List all catalog models and local status")

    # models status <id>
    status_parser = subparsers.add_parser("status", help="Check status of a specific model")
    status_parser.add_argument("model_id", help="Model ID to check")

    # models verify <id>
    verify_parser = subparsers.add_parser("verify", help="Verify filesystem integrity of a model")
    verify_parser.add_argument("model_id", help="Model ID to verify")

    # models remove <id>
    remove_parser = subparsers.add_parser("remove", help="Safely remove a registered model from local storage")
    remove_parser.add_argument("model_id", help="Model ID to remove")

    args = parser.parse_args()

    if args.command == "list" or not args.command:
        models = registry.list_catalog()
        print(f"\n{'MODEL ID':<30} {'FAMILY':<18} {'STATUS':<15} {'SIZE':<10} {'LANGUAGES'}")
        print("=" * 90)
        for m in models:
            langs = ", ".join(m.supported_languages)
            print(f"{m.model_id:<30} {m.family.value:<18} {m.status.value:<15} {m.installed_size_human:<10} {langs}")
        print(f"\nTotal Catalog Models: {len(models)}")

    elif args.command == "status":
        model = registry.get_model(args.model_id)
        if not model:
            print(f"Error: Model '{args.model_id}' not found in catalog.")
            sys.exit(1)
        print(f"\nModel: {model.display_name} ({model.model_id})")
        print(f"Provider: {model.provider_id}")
        print(f"Status: {model.status.value}")
        print(f"Status Detail: {model.status_detail}")
        print(f"Storage Path: {model.local_path}")
        print(f"Size on Disk: {model.installed_size_human}")
        print(f"Supported Languages: {', '.join(model.supported_languages)}")
        print(f"Hardware Notes: {model.hardware_notes}")

    elif args.command == "verify":
        try:
            model = registry.verify_model(args.model_id)
            print(f"Verification result for '{model.model_id}': {model.status.value} - {model.status_detail}")
        except Exception as e:
            print(f"Verification failed: {e}")
            sys.exit(1)

    elif args.command == "remove":
        model = registry.get_model(args.model_id)
        if not model:
            print(f"Error: Model '{args.model_id}' not found in catalog.")
            sys.exit(1)
        target_path = registry.get_model_path(model.family, model.model_id)
        if not target_path.exists():
            print(f"Model '{args.model_id}' is not currently installed at {target_path}.")
            sys.exit(0)
        import shutil
        shutil.rmtree(str(target_path))
        print(f"Successfully removed model '{args.model_id}' from {target_path}.")
        print("Existing transcripts and research records remain fully intact.")

if __name__ == "__main__":
    main()

