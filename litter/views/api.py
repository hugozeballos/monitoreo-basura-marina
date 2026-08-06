from django.http import JsonResponse
from litter.services.beach_summary import get_beaches_summary


def beaches_summary_api(request):
    """
    API endpoint returning beach summaries
    and global statistics for the map.
    """
    data = get_beaches_summary()
    return JsonResponse(data)
# The beaches_summary_api_v2 endpoint allows filtering the beach summaries by year, country, method_id, and minimum density. The filters are passed as query parameters in
def beaches_summary_api_v2(request):
    filters = {
        "year": request.GET.get("year"),
        "country": request.GET.get("country"),
        "method_id": request.GET.get("method_id"),
        "min_density": request.GET.get("min_density"),
    }

    data = get_beaches_summary(filters=filters)
    return JsonResponse(data)
