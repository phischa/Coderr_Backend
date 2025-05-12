from rest_framework import viewsets, status
from rest_framework.decorators import api_view
from rest_framework.response import Response
from django.http import JsonResponse

@api_view(['GET'])
def hello_world(request):
    """
    A simple API view that returns a hello message.
    
    Args:
        request: The HTTP request.
        
    Returns:
        Response: A JSON response with a "Hello World!" message.
    """
    return Response({"message": "Hello World!"})