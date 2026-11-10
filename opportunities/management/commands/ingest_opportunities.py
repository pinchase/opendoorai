from django.core.management.base import BaseCommand, CommandError

from opportunities.ingestion import FeedError, fetch_feed, import_records, load_configured_feeds


class Command(BaseCommand):
    help = "Import normalized records from an explicitly allowlisted HTTPS JSON feed."

    def add_arguments(self, parser):
        parser.add_argument("--feed", required=True, help="Configured feed id from OPPORTUNITY_FEEDS_JSON.")
        parser.add_argument(
            "--publish",
            action="store_true",
            help="Publish validated records; without this flag, new imports remain unpublished for review.",
        )
        parser.add_argument("--dry-run", action="store_true", help="Validate and report without database writes.")

    def handle(self, *args, **options):
        try:
            feeds = load_configured_feeds()
        except FeedError as error:
            raise CommandError(str(error)) from error
        if not feeds:
            raise CommandError("No feeds are configured. Add trusted HTTPS feeds to OPPORTUNITY_FEEDS_JSON.")
        feed = feeds.get(options["feed"])
        if not feed:
            raise CommandError("The requested feed id is not configured.")
        try:
            records = fetch_feed(feed)
        except FeedError as error:
            raise CommandError(f"Feed {feed['id']!r} could not be collected: {error}") from error

        result = import_records(
            records,
            feed,
            publish=options["publish"],
            dry_run=options["dry_run"],
        )
        mode = "Dry run" if options["dry_run"] else "Import complete"
        self.stdout.write(
            f"{mode} for {feed['name']}: "
            f"{result['created']} created, {result['updated']} updated, "
            f"{result['skipped']} skipped."
        )
        for error in result["errors"]:
            self.stderr.write(
                self.style.WARNING(f"Record {error['record']} skipped: {error['reason']}")
            )
