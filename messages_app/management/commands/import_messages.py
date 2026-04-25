import csv
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime

from messages_app.models import Message

# Custom Django management command used to import communication
# records from a CSV dataset into the Message table
class Command(BaseCommand):

    # Help text shown when running:
    # python manage.py help import_messages
    help = "Import messages from CSV file"

    # Adds a required command-line argument for the CSV file path
    def add_arguments(self, parser):
        parser.add_argument("csv_file", type=str)

    # Main command execution method
    def handle(self, *args, **options):

        # Retrieve file path provided by user
        file_path = options["csv_file"]

        # Open CSV file using UTF-8 encoding
        with open(file_path, newline="", encoding="utf-8") as file:

            # Read CSV rows using column headers
            reader = csv.DictReader(file)

            # Counter to report number of processed uploads
            count = 0

            # Convert timestamp string into Python datetime object.
            for row in reader:
                dt = datetime.strptime(row["timestamp"], "%Y-%m-%d %H:%M:%S")

                # Convert naive datetime into timezone-aware datetime
                # for compatibility with Django timezone settings
                aware_dt = timezone.make_aware(dt)

                # Insert new record or update existing record if the same message_id already exists
                # Prevents duplicates
                Message.objects.update_or_create(
                    message_id=row["message_id"],
                    defaults={
                        "timestamp": aware_dt,
                        "channel": row["channel"],
                        "sender_id": row["sender_id"],
                        "sender_name": row["sender_name"],
                        "sender_role": row["sender_role"],
                        "message_text": row["message"],
                        "category": row["category"],
                    },
                )
                count += 1
                
        # Display success message in terminal after import completes
        self.stdout.write(self.style.SUCCESS(f"Imported {count} messages"))