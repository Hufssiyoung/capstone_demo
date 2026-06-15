from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_projectfile_ai_final_grade'),
    ]

    operations = [
        migrations.AddField(
            model_name='filereviewitem',
            name='judgment',
            field=models.CharField(default='FAIL', max_length=20, verbose_name='판정'),
        ),
    ]
