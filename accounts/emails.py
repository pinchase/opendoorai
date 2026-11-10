from django.conf import settings
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.urls import reverse
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_encode


def send_verification_email(request, user):
    uid = urlsafe_base64_encode(force_bytes(user.pk))
    token = default_token_generator.make_token(user)
    verification_url = request.build_absolute_uri(
        reverse("accounts:verify-email", kwargs={"uidb64": uid, "token": token})
    )
    return send_mail(
        subject="Verify your OpenDoors AI email",
        message=(
            f"Hello {user.profile.full_name or user.email},\n\n"
            "Confirm your email address to activate your OpenDoors AI account:\n"
            f"{verification_url}\n\n"
            f"This link expires in {settings.PASSWORD_RESET_TIMEOUT // 3600} hours. "
            "If you did not create this account, you can ignore this message."
        ),
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=[user.email],
        fail_silently=False,
    )
