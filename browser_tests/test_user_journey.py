import uuid
import unittest

from django.contrib.staticfiles.testing import StaticLiveServerTestCase
from django.test import tag

from opportunities.models import Opportunity

try:
    from axe_playwright_python.sync_playwright import Axe
    from playwright.sync_api import sync_playwright
except ImportError as error:
    BROWSER_TEST_IMPORT_ERROR = error
else:
    BROWSER_TEST_IMPORT_ERROR = None


@tag("browser")
@unittest.skipIf(
    BROWSER_TEST_IMPORT_ERROR is not None,
    "Install requirements-dev.txt to run browser and axe checks.",
)
class OpenDoorsBrowserJourneyTests(StaticLiveServerTestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.opportunity = Opportunity.objects.create(
            title="Browser Demo Fellowship",
            organization="OpenDoors Test Data",
            description="A synthetic opportunity for exercising browser discovery and tracking.",
            category="fellowship",
            location="Remote",
            eligibility_requirements="Test data only; review requirements with the provider.",
            required_skills=["research", "communication"],
            required_education="undergraduate",
            application_deadline=None,
            is_demo=True,
            is_published=True,
        )

    @classmethod
    def tearDownClass(cls):
        cls.opportunity.delete()
        super().tearDownClass()

    def assert_accessible(self, page, axe):
        results = axe.run(page, options={
            "runOnly": {
                "type": "tag",
                "values": ["wcag2a", "wcag2aa", "wcag21a", "wcag21aa", "wcag22aa"],
            }
        })
        self.assertEqual(results.violations_count, 0, results.generate_report())

    def test_registration_profile_discovery_match_save_tracker_and_login(self):
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch()
            page = browser.new_page(viewport={"width": 1280, "height": 900})
            axe = Axe()
            email = f"browser-{uuid.uuid4().hex[:12]}@example.test"
            password = "SecureBrowser!2847"
            page.goto(self.live_server_url)

            page.keyboard.press("Tab")
            self.assertEqual(page.locator(":focus").get_attribute("class"), "skip-link")
            self.assert_accessible(page, axe)

            page.locator("#main-content").get_by_role(
                "link", name="Get started"
            ).click()
            page.get_by_label("Full name").fill("Browser Demo User")
            page.get_by_label("Email").fill(email)
            page.get_by_label("Password", exact=True).fill(password)
            page.get_by_label("Confirm password").fill(password)
            page.get_by_role("button", name="Create account").click()
            page.get_by_role("heading", name="Welcome, Browser Demo User").wait_for()

            page.goto(f"{self.live_server_url}/profile/")
            page.get_by_label("Education level").select_option("undergraduate")
            page.get_by_label("Field of study").fill("Computer Science")
            page.get_by_label("Skills").fill("research, communication")
            page.get_by_label("Preferred location").fill("Remote")
            page.locator('input[name="preferred_categories"][value="fellowship"]').check()
            page.get_by_label("Experience level").select_option("beginner")
            page.get_by_role("button", name="Save profile").click()
            page.get_by_text("Your profile has been updated.").wait_for()
            self.assert_accessible(page, axe)

            page.goto(f"{self.live_server_url}/opportunities/")
            page.get_by_role("heading", name="Explore opportunities").wait_for()
            self.assert_accessible(page, axe)
            page.get_by_role("link", name="Browser Demo Fellowship").click()
            page.get_by_role("heading", name="Browser Demo Fellowship").wait_for()
            self.assert_accessible(page, axe)
            page.get_by_role("button", name="Save opportunity").click()
            page.get_by_text("Opportunity saved.").wait_for()
            page.get_by_role("button", name="Add to application tracker").click()
            page.get_by_role("heading", name="Application tracker").wait_for()
            page.get_by_label("Application status").select_option("preparing")
            page.get_by_role("button", name="Update status").click()
            page.get_by_text("Application status updated.").wait_for()
            self.assert_accessible(page, axe)

            page.goto(f"{self.live_server_url}/saved/")
            page.get_by_role("heading", name="Saved opportunities").wait_for()
            page.get_by_role("link", name="Browser Demo Fellowship").wait_for()
            self.assert_accessible(page, axe)

            page.goto(f"{self.live_server_url}/matches/")
            page.get_by_role("heading", name="Your opportunity matches").wait_for()
            page.get_by_role("link", name="Browser Demo Fellowship").wait_for()
            self.assert_accessible(page, axe)

            page.set_viewport_size({"width": 375, "height": 812})
            page.goto(self.live_server_url)
            self.assertLessEqual(
                page.evaluate("document.documentElement.scrollWidth"),
                page.evaluate("window.innerWidth"),
                "The landing page should not overflow at a narrow viewport.",
            )
            page.emulate_media(reduced_motion="reduce")
            self.assert_accessible(page, axe)

            page.locator(".account-menu summary").click()
            page.get_by_role("button", name="Log out").click()
            page.get_by_role("link", name="Log in").wait_for()
            page.get_by_role("link", name="Log in").click()
            page.get_by_label("Email").fill(email)
            page.get_by_label("Password", exact=True).fill(password)
            page.get_by_role("button", name="Log in").click()
            page.get_by_role("heading", name="Welcome, Browser Demo User").wait_for()
            browser.close()
