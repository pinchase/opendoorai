from datetime import date

from profiles.models import Profile

MATCH_WEIGHTS = {
    "skills": 30,
    "education": 25,
    "field_of_study": 20,
    "experience": 15,
    "location": 10,
    "category": 10,
}

EDUCATION_RANK = {
    "secondary": 0,
    "vocational": 1,
    "undergraduate": 2,
    "graduate": 3,
    "postgraduate": 4,
}
EXPERIENCE_RANK = {
    "none": 0,
    "beginner": 1,
    "intermediate": 2,
    "experienced": 3,
}
PROFILE_FIELDS = {
    "education_level": "education level",
    "field_of_study": "field of study",
    "experience_level": "experience level",
    "preferred_location": "preferred location",
    "graduation_year": "graduation year",
    "institution": "institution",
    "skills": "skills",
}


def _normalized(value):
    return str(value or "").strip().casefold()


def _field_match(profile_value, opportunity_value):
    required = _normalized(opportunity_value)
    if not required or not _normalized(profile_value):
        return None
    return 1.0 if required in _normalized(profile_value) or _normalized(profile_value) in required else 0.0


def _mandatory_results(profile, opportunity):
    met, missing, unmet = [], [], []
    requirements = opportunity.mandatory_requirements or []
    if not isinstance(requirements, list):
        return met, ["Mandatory requirements could not be checked; confirm them with the provider."], unmet
    for requirement in requirements:
        if not isinstance(requirement, dict):
            missing.append("A mandatory requirement could not be checked; confirm it with the provider.")
            continue
        field = requirement.get("profile_field", "")
        if not isinstance(field, str):
            missing.append("A mandatory requirement could not be checked; confirm it with the provider.")
            continue
        label = str(requirement.get("label") or PROFILE_FIELDS.get(field, field.replace("_", " ")))
        if field not in PROFILE_FIELDS:
            missing.append(f"Requirement could not be checked: {label}.")
            continue
        value = getattr(profile, field, None)
        if value in ("", None, [], {}):
            missing.append(f"Confirm {label} to check this mandatory requirement.")
            continue
        operator = requirement.get("operator", "in")
        if not isinstance(operator, str) or operator not in {"in", "equals"}:
            missing.append(f"Confirm how to check the mandatory requirement: {label}.")
            continue
        expected = requirement.get("values", [])
        if not isinstance(expected, list):
            expected = [expected]
        if not expected:
            missing.append(f"Confirm the details for mandatory requirement: {label}.")
            continue
        normalized_expected = {_normalized(item) for item in expected}
        actual = _normalized(value)
        passed = (
            actual in normalized_expected
            if operator == "in"
            else actual == _normalized(expected[0]) if operator == "equals" and expected else False
        )
        if passed:
            met.append(f"Meets mandatory requirement: {label}.")
        else:
            unmet.append(f"Mandatory requirement may not be met: {label}.")
    return met, missing, unmet


def score_opportunity(profile: Profile, opportunity) -> dict:
    """Return a deterministic, explainable match; unknown dimensions do not count against a profile."""
    scores = {}
    reasons, qualifications, missing = [], [], []

    raw_required_skills = opportunity.required_skills or []
    required_skills = {
        _normalized(skill) for skill in raw_required_skills if isinstance(skill, str) and _normalized(skill)
    } if isinstance(raw_required_skills, list) else set()
    if required_skills and profile.normalized_skills:
        overlap = required_skills & profile.normalized_skills
        scores["skills"] = len(overlap) / len(required_skills)
        if overlap:
            qualifications.append("Skills: " + ", ".join(sorted(overlap)))
            reasons.append(f"Your skills match {len(overlap)} of {len(required_skills)} listed skills.")
        else:
            reasons.append("No listed required skills match the skills in your profile.")
    elif raw_required_skills and not isinstance(raw_required_skills, list):
        missing.append("Required skills could not be assessed; confirm them with the provider.")
    elif required_skills:
        missing.append("Add your skills to assess skills compatibility.")
    else:
        missing.append("The opportunity does not list required skills.")

    if opportunity.required_education and profile.education_level:
        user_rank = EDUCATION_RANK.get(profile.education_level)
        required_rank = EDUCATION_RANK.get(opportunity.required_education)
        if user_rank is not None and required_rank is not None:
            scores["education"] = float(user_rank >= required_rank)
            if scores["education"]:
                qualifications.append(f"Education: {profile.get_education_level_display()}")
                reasons.append("Your education level meets the listed education level.")
            else:
                reasons.append("Your current education level is below the listed level.")
    elif opportunity.required_education:
        missing.append("Add your education level to assess education compatibility.")

    field_match = _field_match(profile.field_of_study, opportunity.required_field)
    if field_match is not None:
        scores["field_of_study"] = field_match
        if field_match:
            qualifications.append(f"Field of study: {profile.field_of_study}")
            reasons.append("Your field of study aligns with the opportunity.")
        else:
            reasons.append("Your field of study does not appear to align with the listed field.")
    elif opportunity.required_field:
        missing.append("Add your field of study to assess subject compatibility.")

    if opportunity.required_experience and profile.experience_level:
        actual = EXPERIENCE_RANK.get(profile.experience_level)
        required = EXPERIENCE_RANK.get(opportunity.required_experience)
        if actual is not None and required is not None:
            scores["experience"] = float(actual >= required)
            reasons.append(
                "Your experience level meets the listed level."
                if scores["experience"]
                else "Your experience level is below the listed level."
            )
    elif opportunity.required_experience:
        missing.append("Add your experience level to assess experience compatibility.")

    if opportunity.location and profile.preferred_location:
        location = _normalized(opportunity.location)
        preference = _normalized(profile.preferred_location)
        flexible = "remote" in location or "anywhere" in preference
        scores["location"] = float(flexible or location == preference or preference in location)
        reasons.append(
            "The location matches your preference."
            if scores["location"]
            else "The listed location differs from your preference; check whether relocation or remote work is possible."
        )
    elif opportunity.location:
        missing.append("Add your preferred location to assess location compatibility.")

    if profile.preferred_categories:
        scores["category"] = float(opportunity.category in profile.preferred_categories)
        reasons.append(
            "This is one of your preferred categories."
            if scores["category"]
            else "This category is not in your current preferences."
        )
    else:
        missing.append("Add preferred categories to assess category alignment.")

    applicable_weight = sum(MATCH_WEIGHTS[key] for key in scores)
    score = round(
        sum(MATCH_WEIGHTS[key] * value for key, value in scores.items()) / applicable_weight * 100
    ) if applicable_weight else 0

    met, mandatory_missing, unmet = _mandatory_results(profile, opportunity)
    reasons.extend(met)
    missing.extend(mandatory_missing)
    mandatory_unmet = list(unmet)
    concerns = list(unmet)
    level = "strong" if score >= 75 else "good" if score >= 50 else "possible"
    if opportunity.application_deadline and opportunity.application_deadline < date.today():
        concerns.append("The listed application deadline has passed; confirm the opportunity is still open.")
    next_steps = ["Review the complete eligibility requirements before applying."]
    if missing:
        next_steps.append("Complete the missing profile details to improve this assessment.")
    if opportunity.application_url:
        next_steps.append("Confirm the application instructions and deadline on the provider's page.")
    return {
        "score": max(0, min(100, score)),
        "level": level,
        "reasons": reasons or ["There is not enough profile or opportunity information to assess fit."],
        "relevant_qualifications": qualifications,
        "missing_information": list(dict.fromkeys(missing)),
        "eligibility_concerns": concerns,
        "eligibility_status": "not_eligible" if mandatory_unmet else "review_requirements",
        "next_steps": next_steps,
        "dimension_scores": {key: round(value * 100) for key, value in scores.items()},
    }


def rank_opportunities(profile, opportunities):
    ranked = [
        {"opportunity": opportunity, **score_opportunity(profile, opportunity)}
        for opportunity in opportunities
    ]
    return sorted(ranked, key=lambda result: (-result["score"], result["opportunity"].application_deadline or date.max))
