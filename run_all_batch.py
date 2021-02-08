from main_batch_mode import main

# "classic_tls", "classic_precedence", "reservation", "auction"

if __name__ == "__main__":
    projects = ["classic_tls", "classic_precedence", "reservation", "auction"]
    for project in projects:
        print(f"\nEseguo progetto {project}...")
        main(project)
