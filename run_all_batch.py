from main_batch_mode import main

if __name__ == "__main__":
    projects = ["classic_precedence_three_lanes", "classic_tls_three_lanes"]
    for project in projects:
        print(f"\nEseguo progetto {project}...")
        main(project)
