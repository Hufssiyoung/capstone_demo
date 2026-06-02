from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_filereviewitem_judgment'),
    ]

    operations = [
        migrations.AddField(
            model_name='filereviewitem',
            name='node',
            field=models.CharField(blank=True, default='', max_length=50, verbose_name='검증 노드'),
        ),
    ]
