from rest_framework import serializers
from rest_framework.pagination import PageNumberPagination
from rest_framework.response import Response


class CustomUserSerializer(serializers.Serializer):
    username = serializers.CharField(read_only=True)
    full_name = serializers.CharField(source='get_full_name', read_only=True)


class CustomPagination(PageNumberPagination):
    """Same response format as used by django-shop"""
    page_size = 2
    page_size_query_param = 'page_size'

    def get_paginated_response(self, data):
        return Response({
            'count': self.page.paginator.count,
            'totalPages': self.page.paginator.num_pages,
            'currentPage': self.page.number,
            'pageSize': self.get_page_size(self.request),
            'results': data
        })
