from rest_framework import status, generics
from rest_framework.generics import get_object_or_404
from rest_framework.permissions import IsAuthenticated, SAFE_METHODS
from rest_framework.response import Response
from rest_framework.views import APIView

from accounts.permissions import IsCharityOwner, IsBenefactor
from charities.models import Task
from charities.serializers import (
    TaskSerializer, CharitySerializer, BenefactorSerializer
)


class BenefactorRegistration(APIView):
    def post(self, request):
        benefactor_serializer = BenefactorSerializer(data=request.data)
        
        if benefactor_serializer.is_valid():
            benefactor_serializer.save(user=request.user)
            return Response(status=status.HTTP_201_CREATED)
        
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class CharityRegistration(APIView):
    def post(self, request):
        charity_serializer = CharitySerializer(data=request.data)
        
        if charity_serializer.is_valid():
            charity_serializer.save(user=request.user)
            return Response(status=status.HTTP_201_CREATED)
        
        else:
            return Response(status=status.HTTP_400_BAD_REQUEST)


class Tasks(generics.ListCreateAPIView):
    serializer_class = TaskSerializer

    def get_queryset(self):
        return Task.objects.all_related_tasks_to_user(self.request.user)

    def post(self, request, *args, **kwargs):
        data = {
            **request.data,
            "charity_id": request.user.charity.id
        }
        serializer = self.serializer_class(data = data)
        serializer.is_valid(raise_exception = True)
        serializer.save()
        return Response(serializer.data, status = status.HTTP_201_CREATED)

    def get_permissions(self):
        if self.request.method in SAFE_METHODS:
            self.permission_classes = [IsAuthenticated, ]
        else:
            self.permission_classes = [IsCharityOwner, ]

        return [permission() for permission in self.permission_classes]

    def filter_queryset(self, queryset):
        filter_lookups = {}
        for name, value in Task.filtering_lookups:
            param = self.request.GET.get(value)
            if param:
                filter_lookups[name] = param
        exclude_lookups = {}
        for name, value in Task.excluding_lookups:
            param = self.request.GET.get(value)
            if param:
                exclude_lookups[name] = param

        return queryset.filter(**filter_lookups).exclude(**exclude_lookups)


class TaskRequest(APIView):
    permission_classes = [IsAuthenticated, IsBenefactor]
    
    def get(self, request, task_id):
        if Task.objects.filter(id=task_id).exists():
            task = Task.objects.get(id=task_id)
            
            if (task.state != 'P'):
                data={'detail': 'This task is not pending.'}
                return Response(data, status=status.HTTP_404_NOT_FOUND)
            
            else:
                task.assign_to_benefactor(request.user.benefactor)
                data={'detail': 'Request sent.'}
                return Response(data, status=status.HTTP_200_OK)
        
        else:
            return Response(status=status.HTTP_404_NOT_FOUND)


class TaskResponse(APIView):
    permission_classes = [IsAuthenticated, IsCharityOwner]
    
    def post(self, request, task_id):
        task_status = request.data['response']
        
        if Task.objects.filter(id=task_id).exists():
            task = Task.objects.get(id=task_id)
        
        if ((task_status != 'A') and (task_status != 'R')):
            data={'detail': 'Required field ("A" for accepted / "R" for rejected)'}
            return Response(data, status=status.HTTP_400_BAD_REQUEST)
        
        if (task.state != 'W'):
            data={'detail': 'This task is not waiting.'}
            return Response(data, status=status.HTTP_404_NOT_FOUND)
        
        if (task_status == 'A'):
            data={'detail': 'Response sent.'}
            task._accept_benefactor()
            return Response(data, status=status.HTTP_200_OK)
        
        if (task_status == 'R'):
            data={'detail': 'Response sent.'}
            task._reject_benefactor()
            return Response(data, status=status.HTTP_200_OK)
            


class DoneTask(APIView):
    pass