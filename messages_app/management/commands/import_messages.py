import csv
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import datetime

from messages_app.choices import UploadStatus
from messages_app.models import Message, UploadBatch


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

        def handle(self, *args, **options):
            # Path of uploaded CSV file
            file_path = options["csv_file"]

            # Create upload session record
            batch = UploadBatch.objects.create(
                filename=file_path,
                status=UploadStatus.PROCESSING
            )

            success_count = 0
            failed_count = 0
            errors = []

            try:
            # Open CSV file using UTF-8 encoding
                with open(file_path, newline="", encoding="utf-8") as file:

                    # Read CSV rows using column headers
                    reader = csv.DictReader(file)

                    # Convert timestamp string into Python datetime object.
                    for row_number, row in enumerate(reader, start=2):

                        try:
                            # Parse timestamp text
                            dt = datetime.strptime(
                                row["timestamp"],
                                "%Y-%m-%d %H:%M:%S"
                            )

                            # Convert to timezone aware datetime
                            aware_dt = timezone.make_aware(dt)

                            # Insert or update existing message
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
                                    "batch": batch,
                                },
                            )

                            success_count += 1

                        except Exception as row_error:
                            # Row failed but continue import
                            failed_count += 1
                            errors.append(
                                f"Row {row_number}: {str(row_error)}"
                            )

                    # Import completed successfully
                    batch.total_records = success_count
                    batch.failed_records = failed_count
                    batch.error_log = "\n".join(errors[:50])
                    batch.status = UploadStatus.COMPLETE
                    batch.save()

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Imported {success_count} messages "
                            f"({failed_count} failed)"
                        )
                    )


            except Exception as exc:

                batch.failed_records = failed_count
                batch.error_log = str(exc)
                batch.status = UploadStatus.FAILED
                batch.save()

                self.stdout.write(
                    self.style.ERROR(
                        f"Import failed: {str(exc)}"
                    )
                )
