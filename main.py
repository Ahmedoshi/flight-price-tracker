from app.config.settings import settings, PROJECT_ROOT


def main():
    print("=" * 45)
    print(" Flight Price Tracker")
    print(" Version 1.0")
    print("=" * 45)
    print()

    print("✓ Configuration loaded")
    print(f"✓ Project Root : {PROJECT_ROOT}")
    print(f"✓ Database     : {settings.database_path}")
    print(f"✓ Timezone     : {settings.timezone}")
    print(f"✓ Check Every  : {settings.check_interval} hour(s)")
    print()

    print("Application started successfully.")


if __name__ == "__main__":
    main()