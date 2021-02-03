from main_batch_mode import main

# "classic_tls_three_lanes", "classic_tls_three_lanes", "reservation", "auctions"

if __name__ == "__main__":
    projects = ["classic_tls_three_lanes", "classic_tls_three_lanes", "reservation", "auctions"]
    for project in projects:
        print(f"\nEseguo progetto {project}...")
        main(project)
