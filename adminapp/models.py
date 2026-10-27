from django.db import models

# Create your models here.

class tbl_admin(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=100)
    role = models.CharField(max_length=100)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Admin"
        verbose_name_plural = "Admins"

    def __str__(self):
        return self.name

# Alias for backwards compatibility
AdminLogin = tbl_admin


class Category(models.Model):
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    class Meta:
        verbose_name = "Category"
        verbose_name_plural = "Categories"

    def __str__(self):
        return self.name


class Officer(models.Model):
    GENDER_CHOICES = [
        ('Male', 'Male'),
        ('Female', 'Female'),
    ]

    Fullname = models.CharField(max_length=50)
    Email = models.EmailField()
    Password = models.CharField(max_length=50)
    Phone = models.CharField(max_length=10)
    Gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    id_card = models.ImageField(null=True, blank=True, upload_to='id_cards/')
    category = models.ForeignKey(Category, on_delete=models.CASCADE, related_name='officers')
    officer_id = models.CharField(max_length=255)
    profile = models.ImageField(null=True, blank=True, upload_to='profiles/')

    class Meta:
        verbose_name = "Officer"
        verbose_name_plural = "Officers"

    def __str__(self):
        return self.Fullname