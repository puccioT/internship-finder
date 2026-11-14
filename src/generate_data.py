import pandas as pd
import random
import os

def generate_mock_internships(num_offers=500):
    domains = ["Product Management", "Data Analysis", "Product Operations", "Strategy & Operations", "Project Management"]
    locations = ["Paris", "London", "Berlin", "Amsterdam", "Lyon", "Remote", "Madrid", "Munich", "Barcelona", "Dublin"]
    companies = ["TechScale", "DataStart", "BizDev", "FinTech Plus", "CloudNine", "RetailAI", "MobilityGo", "DeepTech", "PayFlow", "HealthCare Co", "GreenEnergy", "WebAgency", "Doctolib", "Qonto", "Alan", "Back Market", "BlaBlaCar", "Criteo", "Datadog", "Revolut"]
    
    contract_types = ["End-of-study Internship", "Gap Year (Césure)", "Part-time (Alternance)"]
    english_levels = ["Professional", "Fluent/Native", "Basic"]

    skills_pool = {
        "Product Management": ["Python", "Figma", "Agile", "SQL", "Jira", "Notion", "Roadmapping", "A/B Testing", "User Research"],
        "Data Analysis": ["SQL", "Python", "Pandas", "Tableau", "PowerBI", "Looker", "Machine Learning", "R", "Excel", "Data Cleaning"],
        "Product Operations": ["SQL", "Excel", "Process", "Jira", "Notion", "Automation", "Zapier", "Stakeholder Management"],
        "Strategy & Operations": ["Excel", "Strategy", "Sales", "Notion", "PowerPoint", "Financial Modeling", "CRM", "Go-to-market"],
        "Project Management": ["Trello", "Communication", "Organization", "Agile", "Scrum", "Asana", "Client Management"]
    }

    action_verbs = ["Lead", "Support", "Automate", "Analyze", "Optimize", "Build", "Scale", "Manage", "Design"]
    impact_nouns = ["growth metrics", "user retention", "product pipelines", "conversion funnels", "operational efficiency", "data dashboards"]

    data = []
    for i in range(1, num_offers + 1):
        domain = random.choice(domains)
        company = random.choice(companies)
        
        # Sélection aléatoire de 3 à 5 compétences pertinentes pour le domaine
        domain_skills = random.sample(skills_pool[domain], random.randint(3, 5))
        skills_str = ";".join(domain_skills)
        
        title = f"{random.choice(['Junior', 'Associate', 'Intern'])} {domain}"
        
        # Génération d'une description synthétique réaliste
        verb = random.choice(action_verbs)
        noun = random.choice(impact_nouns)
        desc = f"Join {company} to {verb.lower()} our {noun}. You will work with the core team using {domain_skills[0]} and {domain_skills[1]} to drive strategic decisions."
        
        data.append({
            "id": i,
            "title": title,
            "company": company,
            "location": random.choice(locations),
            "domain": domain,
            "skills": skills_str,
            "description": desc,
            "contract_type": random.choice(contract_types),
            "english_level": random.choice(english_levels)
        })

    df = pd.DataFrame(data)
    
    # Assure-toi que le dossier data existe
    os.makedirs("data", exist_ok=True)
    df.to_csv("data/internships.csv", index=False)
    print(f"✅ Successfully generated {num_offers} internship offers in data/internships.csv")

if __name__ == "__main__":
    generate_mock_internships(500)