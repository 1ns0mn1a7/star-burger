from django.db import models


class Place(models.Model):
    address = models.CharField(
        'Адрес',
        max_length=255,
        unique=True,
        help_text='Адрес места (например, улица и дом)'
    )
    coordinates = models.JSONField(
        'Координаты',
        null=True,
        blank=True,
        help_text='Координаты в формате [широта, долгота]'
    )
    updated_at = models.DateTimeField(
        'Дата обновления',
        auto_now=True,
        help_text='Когда координаты были обновлены'
    )

    class Meta:
        verbose_name = 'Место'
        verbose_name_plural = 'Места'
        ordering = ['address']

    def __str__(self):
        return self.address
