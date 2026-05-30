from django.db import models


class SchoolClass(models.Model):
    """A class/grade in the school, e.g., 'Form 1A', 'Grade 6B'."""
    name = models.CharField(max_length=50, unique=True)
    grade_level = models.PositiveSmallIntegerField()
    section = models.CharField(max_length=5, blank=True)
    academic_year = models.CharField(max_length=10)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['grade_level', 'section']
        verbose_name_plural = 'School classes'

    def __str__(self):
        return self.name

    @property
    def student_count(self):
        return self.students.filter(is_active=True).count()

    @property
    def boys_count(self):
        return self.students.filter(is_active=True, gender='M').count()

    @property
    def girls_count(self):
        return self.students.filter(is_active=True, gender='F').count()


class Subject(models.Model):
    """Subjects taught in the school."""
    name = models.CharField(max_length=100, unique=True)
    code = models.CharField(max_length=20, unique=True)
    description = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.code} - {self.name}"
