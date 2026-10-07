from django.conf import settings


def promotion(request):
    return {"promo_start": settings.PROMO_START, "promo_end": settings.PROMO_END, "promo_timezone": settings.TIME_ZONE}
