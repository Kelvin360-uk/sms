from django.db import models
from django.conf import settings


class Teacher(models.Model):
    GENDER_CHOICES = [('M', 'Male'), ('F', 'Female')]
    STAFF_TYPE = [('TEACHING', 'Teaching'), ('NON_TEACHING', 'Non-Teaching')]

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                 related_name='teacher_profile')
    employee_id = models.CharField(max_length=30, unique=True, db_index=True)
    full_name = models.CharField(max_length=200, db_index=True)
    date_of_birth = models.DateField(null=True, blank=True)
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES)
    residence = models.CharField(max_length=200)
    phone = models.CharField(max_length=20)
    email = models.EmailField()

    staff_type = models.CharField(max_length=20, choices=STAFF_TYPE, default='TEACHING')

    subjects_taught = models.ManyToManyField('classes.Subject', blank=True, related_name='teachers')
    classes_taught = models.ManyToManyField('classes.SchoolClass', blank=True, related_name='subject_teachers')

    is_class_teacher = models.BooleanField(default=False)
    assigned_class = models.OneToOneField('classes.SchoolClass', on_delete=models.SET_NULL,
                                           null=True, blank=True, related_name='class_teacher')

    hire_date = models.DateField(auto_now_add=True)
    is_active = models.BooleanField(default=True)
    photo = models.ImageField(upload_to='profiles/teachers/', blank=True, null=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['full_name']
        indexes = [
            models.Index(fields=['employee_id']),
            models.Index(fields=['full_name']),
            models.Index(fields=['gender']),
        ]

    def __str__(self):
        return f"{self.full_name} ({self.employee_id})"
