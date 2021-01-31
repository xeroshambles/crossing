from main_batch_mode import main

# "classic_precedence_three_lanes", "classic_tls_three_lanes",

if __name__ == "__main__":
    projects = ["classic_precedence_three_lanes", "classic_tls_three_lanes", "reservation"]
    for project in projects:
        print(f"\nEseguo progetto {project}...")
        main(project)
