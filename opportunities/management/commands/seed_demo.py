from django.core.management.base import BaseCommand

from opportunities.models import Opportunity


DEMO_OPPORTUNITIES = [
    {
        "title": "Demonstration: Community Technology Scholarship",
        "category": "scholarship",
        "description": "A sample scholarship listing used to demonstrate how learners can review study support and compare it with their goals.",
        "eligibility_requirements": "Demonstration requirement: currently pursuing an undergraduate course of study. Confirm real requirements with a provider before relying on this sample.",
        "required_education": "undergraduate",
        "required_field": "technology",
        "required_skills": ["communication", "research"],
        "mandatory_requirements": [
            {"profile_field": "education_level", "operator": "in", "values": ["undergraduate"], "label": "undergraduate study"}
        ],
    },
    {
        "title": "Demonstration: Junior Data Internship",
        "category": "internship",
        "description": "A synthetic early-career internship example for practicing data analysis, teamwork, and clear communication.",
        "eligibility_requirements": "Demonstration requirement: introductory data skills and interest in learning from a project team.",
        "required_education": "undergraduate",
        "required_field": "data",
        "required_experience": "beginner",
        "required_skills": ["spreadsheets", "python", "communication"],
    },
    {
        "title": "Demonstration: Entry-Level Program Assistant",
        "category": "job",
        "description": "A fictional entry-level role example focused on coordination, written communication, and supporting a small team.",
        "eligibility_requirements": "Demonstration requirement: organized, clear communication and a willingness to learn. No live vacancy is represented.",
        "required_education": "secondary",
        "required_experience": "none",
        "required_skills": ["organization", "writing"],
    },
    {
        "title": "Demonstration: Emerging Leaders Fellowship",
        "category": "fellowship",
        "description": "A sample fellowship record that illustrates how a learner can compare leadership interests and experience with a program description.",
        "eligibility_requirements": "Demonstration requirement: interest in community leadership and collaborative learning.",
        "required_field": "community",
        "required_experience": "beginner",
        "required_skills": ["leadership", "communication"],
    },
    {
        "title": "Demonstration: Digital Skills Training",
        "category": "training",
        "description": "A fictional short-course opportunity for people who want to build practical digital and problem-solving skills.",
        "eligibility_requirements": "Demonstration requirement: an interest in developing digital skills. No real enrollment link or schedule is available.",
        "required_education": "secondary",
        "required_skills": ["problem solving"],
    },
    {
        "title": "Demonstration: Research Pathways Program",
        "category": "other",
        "description": "A synthetic educational program listing to show how experience and field-of-study requirements appear in a match explanation.",
        "eligibility_requirements": "Demonstration requirement: interest in research and a willingness to learn research methods.",
        "required_education": "undergraduate",
        "required_field": "research",
        "required_skills": ["research", "writing"],
    },
]


class Command(BaseCommand):
    help = "Create clearly labeled synthetic OpenDoors demonstration opportunities."

    def handle(self, *args, **options):
        created_count = 0
        for data in DEMO_OPPORTUNITIES:
            _, created = Opportunity.objects.update_or_create(
                title=data["title"],
                is_demo=True,
                defaults={
                    **data,
                    "organization": "OpenDoors AI Demo Data",
                    "location": "Demonstration only",
                    "opportunity_type": "Synthetic example",
                    "source": "Synthetic demonstration record",
                    "application_url": "",
                    "application_deadline": None,
                    "is_published": True,
                },
            )
            created_count += int(created)
        self.stdout.write(self.style.SUCCESS(
            f"Demo data ready: {created_count} new synthetic opportunities; no live links or deadlines."
        ))
