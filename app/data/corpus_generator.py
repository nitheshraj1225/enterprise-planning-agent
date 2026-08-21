"""
app/data/corpus_generator.py

Synthetic enterprise corpus generator — produces up to 500 synthetic
documents across 5 categories (historical Epics, ERP records, velocity
reports, finance policies, sizing policies) for the RAG layer to index
later (Module 5).

Rule #8 (struggle-before-code) is deliberately waived for this file per
Nithesh's explicit instruction — this is bulk synthetic data generation,
not a concept to be learned through implementation struggle.

Run directly to generate the full corpus:
    python -m app.data.corpus_generator
"""

import os
import random

# ---------------------------------------------------------------------
# Data pools — used across categories for randomized, varied content
# ---------------------------------------------------------------------

TEAM_NAMES = [
    "Payments Platform", "Core Banking", "Customer Onboarding",
    "Risk & Compliance", "Data Platform", "Mobile Experience",
    "Enterprise Integration", "Treasury Systems",
]
SYSTEM_NAMES = [
    "reporting module", "billing engine", "notification service",
    "identity management system", "document management system",
    "workflow automation engine", "customer data platform",
]
STORY_POINTS = [1, 2, 3, 5, 8, 13, 21]
STATUSES = [
    "Open", "Ready for Scope", "Prioritized", "In Progress",
    "QA", "UAT", "Released to Prod", "Done",
]
QUARTERS = ["Q1 FY26", "Q2 FY26", "Q3 FY26", "Q4 FY26", "Q1 FY27"]
COST_CENTERS = [
    "CC-100 Finance", "CC-200 Operations", "CC-300 Technology", "CC-400 Product",
]
STAKEHOLDER_ROLES = [
    "Finance Lead", "Product Owner", "Engineering Director",
    "Compliance Officer", "VP Operations",
]
PROJECT_TYPES = [
    "Infrastructure", "Customer-Facing", "Internal Tooling",
    "Compliance", "Data Migration",
]


# ---------------------------------------------------------------------
# Generators — one per document category, each returns a dict of fields
# ---------------------------------------------------------------------

def generate_epic(epic_id: int) -> dict:
    team = random.choice(TEAM_NAMES)
    system = random.choice(SYSTEM_NAMES)
    points = random.choice(STORY_POINTS)
    status = random.choice(STATUSES)
    quarter = random.choice(QUARTERS)
    dependency_flag = random.choice([True, False])

    title = f"Migrate {system} for {team}"
    description = (
        f"This Epic covers work to {title.lower()}, targeted for {quarter}. "
        f"Current status: {status}. Estimated at {points} story points."
        + (" This Epic has a cross-team dependency that must be resolved before completion."
           if dependency_flag else "")
    )

    return {
        "epic_id": f"EPIC-{epic_id:04d}",
        "title": title,
        "team": team,
        "story_points": points,
        "status": status,
        "quarter": quarter,
        "dependency_flag": dependency_flag,
        "description": description,
    }


def generate_erp_record(record_id: int) -> dict:
    project_id = f"PRJ-{record_id:04d}"
    cost_center = random.choice(COST_CENTERS)
    allocated_budget = random.randint(50, 900) * 1000
    resources_assigned = random.randint(2, 15)
    fiscal_quarter = random.choice(QUARTERS)
    utilization_pct = random.randint(40, 100)

    description = (
        f"ERP record for {project_id}, allocated under {cost_center} with a "
        f"budget of ${allocated_budget:,} for {fiscal_quarter}. "
        f"{resources_assigned} resources assigned, running at "
        f"{utilization_pct}% utilization."
    )

    return {
        "record_id": f"ERP-{record_id:04d}",
        "project_id": project_id,
        "cost_center": cost_center,
        "allocated_budget": allocated_budget,
        "resources_assigned": resources_assigned,
        "fiscal_quarter": fiscal_quarter,
        "utilization_pct": utilization_pct,
        "description": description,
    }


def generate_velocity_report(report_id: int) -> dict:
    team = random.choice(TEAM_NAMES)
    sprint_number = random.randint(1, 26)
    committed_points = random.randint(20, 60)
    completed_points = random.randint(int(committed_points * 0.5), committed_points)
    capacity_hours = random.randint(200, 500)
    quarter = random.choice(QUARTERS)

    description = (
        f"{team} completed {completed_points} of {committed_points} committed "
        f"story points in Sprint {sprint_number} ({quarter}), against a team "
        f"capacity of {capacity_hours} hours."
    )

    return {
        "report_id": f"VEL-{report_id:04d}",
        "team": team,
        "sprint_number": sprint_number,
        "committed_points": committed_points,
        "completed_points": completed_points,
        "capacity_hours": capacity_hours,
        "quarter": quarter,
        "description": description,
    }


def generate_finance_policy(policy_id: int) -> dict:
    approval_threshold = random.choice([25000, 50000, 100000, 250000, 500000])
    sign_off_role = random.choice(STAKEHOLDER_ROLES)
    project_type = random.choice(PROJECT_TYPES)

    description = (
        f"Any {project_type} project with estimated spend above "
        f"${approval_threshold:,} requires sign-off from a {sign_off_role} "
        f"before funding is released."
    )

    return {
        "policy_id": f"FIN-{policy_id:04d}",
        "approval_threshold": approval_threshold,
        "required_sign_off_role": sign_off_role,
        "applicable_project_type": project_type,
        "description": description,
    }


def generate_sizing_policy(policy_id: int) -> dict:
    point_value = random.choice(STORY_POINTS)
    example_epic_id = f"EPIC-{random.randint(1, 300):04d}"

    criteria_map = {
        1: "a single-line config change with no dependencies",
        2: "a small, well-understood change within one team",
        3: "a standard feature change requiring minor testing",
        5: "a moderately complex change touching 2+ components",
        8: "a multi-team dependency or an external approval requirement",
        13: "a major architectural change or cross-system integration",
        21: "a large initiative that should likely be broken into smaller Epics",
    }
    criteria = criteria_map.get(point_value, "a change of unclear scope")

    description = (
        f"A {point_value}-point Epic typically represents {criteria}. "
        f"See {example_epic_id} for a representative example."
    )

    return {
        "policy_id": f"SIZE-{policy_id:04d}",
        "point_value": point_value,
        "complexity_criteria": criteria,
        "example_epic_reference": example_epic_id,
        "description": description,
    }


# ---------------------------------------------------------------------
# Writer — turns one fields dict into a saved Markdown file
# ---------------------------------------------------------------------

def write_document(category: str, doc_id: str, fields: dict) -> None:
    folder = os.path.join("app", "data", "synthetic_corpus", category)
    os.makedirs(folder, exist_ok=True)

    filepath = os.path.join(folder, f"{doc_id}.md")

    lines = [f"# {doc_id}", ""]
    for key, value in fields.items():
        if key != "description":
            lines.append(f"- **{key}**: {value}")
    lines.append("")
    lines.append(fields.get("description", ""))

    with open(filepath, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))


# ---------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------

def generate_corpus(total: int = 500) -> None:
    # Proportional split: 60% epics, 16% ERP, 12% velocity, 8% finance, 4% sizing
    weights = {
        "epics": 0.60,
        "erp_records": 0.16,
        "velocity_reports": 0.12,
        "finance_policies": 0.08,
        "sizing_policies": 0.04,
    }

    counts = {cat: int(total * pct) for cat, pct in weights.items()}
    # Adjust for rounding so the total matches exactly
    counts["epics"] += total - sum(counts.values())

    generators = {
        "epics": (generate_epic, "epic_id"),
        "erp_records": (generate_erp_record, "record_id"),
        "velocity_reports": (generate_velocity_report, "report_id"),
        "finance_policies": (generate_finance_policy, "policy_id"),
        "sizing_policies": (generate_sizing_policy, "policy_id"),
    }

    summary = {}
    for category, count in counts.items():
        generator_fn, id_field = generators[category]
        for i in range(1, count + 1):
            fields = generator_fn(i)
            write_document(category, fields[id_field], fields)
        summary[category] = count

    print("Synthetic corpus generation complete:")
    for category, count in summary.items():
        print(f"  {category}: {count} documents")
    print(f"Total: {sum(summary.values())} documents")


if __name__ == "__main__":
    generate_corpus()
