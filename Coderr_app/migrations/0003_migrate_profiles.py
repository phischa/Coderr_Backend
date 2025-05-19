from django.db import migrations

def migrate_profiles(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    OldProfile = apps.get_model('user_auth_app', 'Profile')
    BusinessProfile = apps.get_model('Coderr_app', 'BusinessProfile')
    CustomerProfile = apps.get_model('Coderr_app', 'CustomerProfile')
    
    # Für jeden Benutzer mit einem Profil
    for old_profile in OldProfile.objects.all():
        user = old_profile.user
        
        # Erstelle das entsprechende neue Profil
        if old_profile.type == 'business':
            BusinessProfile.objects.create(
                user=user,
                file=old_profile.file,
                location=old_profile.location,
                tel=old_profile.tel,
                description=old_profile.description,
                working_hours=old_profile.working_hours,
                created_at=old_profile.created_at,
                is_guest=old_profile.is_guest
            )
        else:  # 'customer'
            CustomerProfile.objects.create(
                user=user,
                file=old_profile.file,
                location=old_profile.location,
                tel=old_profile.tel,
                created_at=old_profile.created_at,
                is_guest=old_profile.is_guest
            )

def reverse_migrate(apps, schema_editor):
    # Keine Rückwärtsmigration nötig, wenn wir die alten Profile behalten
    pass

class Migration(migrations.Migration):
    dependencies = [
        ('Coderr_app', '0002_businessprofile_customerprofile'),  # Stell sicher, dass dies vor deiner Migration ausgeführt wird
        ('user_auth_app', '0001_initial'),
    ]
    
    operations = [
        migrations.RunPython(migrate_profiles, reverse_migrate),
    ]
