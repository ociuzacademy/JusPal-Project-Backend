from django.db import models

# Create your models here.


class userreg(models.Model):
    fullname = models.CharField(max_length=50)
    password = models.CharField(max_length=50)  
    email = models.EmailField()
    profile = models.ImageField(null=True, blank=True, upload_to='profiles/')

    def __str__(self):
        return self.fullname