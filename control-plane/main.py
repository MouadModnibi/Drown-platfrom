import sys
import logging

from core.deploy import deploy

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python3 main.py <app_name> <repo_path>")
        sys.exit(1)

    try:
        result = deploy(sys.argv[1], sys.argv[2])
        print("\nDeployment Successful")
        print("----------------------")
        for k, v in result.items():
            print(f"{k}: {v}")
    except Exception as e:
        logging.error(e)
        sys.exit(1)
