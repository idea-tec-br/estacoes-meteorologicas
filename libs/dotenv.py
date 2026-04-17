def load_env(filename="config.env"):
    try:
        with open(filename) as f:
            for line in f:
                if "=" in line and not line.startswith("#"):
                    key, value = line.strip().split("=", 1)
                    value = value.strip("\"'")
                    globals()[key] = value

    except OSError:
        print("Warning: No .env file found")
 