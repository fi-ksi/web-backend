#!/usr/bin/env python3
"""
Development database initialization script.
This script creates all the test data programmatically using the database models.
"""

import datetime
import model
from db import session, engine
from model import *


def init_dev_data(destruct: bool = False):
    """Initialize development database with test data."""
    model.Base.metadata.create_all(engine)

    try:
        if destruct:
            session.query(Config).delete()
            session.query(UserNotify).delete()
            session.query(ActiveOrg).delete()
            session.query(Module).delete()
            session.query(Thread).delete()
            session.query(Article).delete()
            session.query(Profile).delete()
            session.query(Task).delete()
            session.query(Wave).delete()
            session.query(User).delete()
            session.query(Year).delete()

        # Create Year
        year_2024 = Year(
            id=1,
            year='2024',
            sealed=False,
            point_pad=0
        )
        session.add(year_2024)
        session.flush()  # Flush to get the ID

        # Create Admin User
        admin_user = User(
            id=1,
            email='admin@localhost',
            github='',
            discord='',
            phone='',
            first_name='Admin',
            nick_name='',
            last_name='Developer',
            sex='male',
            password='$2b$12$8msl2crG4so1cwDiDeFkoeNTwnSLHSusmkbuNintOov0dLb9ihuKa',
            short_info='',
            profile_picture='',
            role='admin',
            enabled=True,
            registered=datetime.datetime(2000, 1, 1, 0, 0, 0),
            last_logged_in=datetime.datetime(2024, 8, 10, 15, 43, 25, 227080)
        )
        session.add(admin_user)
        session.flush()

        # Create Wave
        first_wave = Wave(
            id=1,
            year=1,
            index=1,
            caption='First Wave',
            garant=1,
            time_published=datetime.datetime(2098, 12, 31, 23, 0, 0)
        )
        session.add(first_wave)
        session.flush()

        # Create Thread
        first_thread = Thread(
            id=1,
            title='First Task Name',
            public=True,
            year=1
        )
        session.add(first_thread)
        session.flush()

        # Create Task
        first_task = Task(
            id=1,
            title='First Task Name',
            author=1,
            wave=1,
            intro='This text is shown in a popup on hover.',
            body='<p>Content of the first task.</p>',
            solution='<p>Solution.</p>\n<h3 id="h2">H2</h3>\n<p>More solution.</p>\n',
            thread=1,
            time_created=datetime.datetime(2024, 8, 10, 15, 43, 35, 120071),
            time_deadline=datetime.datetime(2099, 1, 1, 23, 59, 59),
            evaluation_public=False,
            git_path='2024/vlna1/uloha_01_first_task',
            git_branch='master',
            git_commit='7bef31b57bb0d57167fb86a998218be35b74782b'
        )
        session.add(first_task)
        session.flush()

        # Create Profile
        admin_profile = Profile(
            user_id=1,
            addr_street='Street 1',
            addr_city='City',
            addr_zip='123',
            addr_country='cz',
            school_name='Uni',
            school_street='Street Uni',
            school_city='City Uni',
            school_zip='456',
            school_country='cz',
            school_finish=2000,
            tshirt_size='NA'
        )
        session.add(admin_profile)

        # Create Article
        welcome_article = Article(
            id=1,
            author=1,
            title='Welcome to the test site!',
            body='<p>This is a test site with a very simple testing content.</p>',
            time_created=datetime.datetime(1999, 12, 31, 23, 0, 0),
            published=True,
            year=1,
            resource='articles/1'
        )
        session.add(welcome_article)

        # Create Modules
        file_module = Module(
            id=1,
            task=1,
            type='general',
            name='File submission module',
            description='<p>Feel free to try it out</p>\n',
            max_points=10,
            autocorrect=False,
            order=0,
            bonus=False,
            custom=False,
            data='{}'
        )
        session.add(file_module)

        programming_module = Module(
            id=2,
            task=1,
            type='programming',
            name='Programming module',
            description='<p>Your task is to write a function that check if a number is odd or even.</p>\n',
            max_points=2,
            autocorrect=True,
            order=1,
            bonus=False,
            custom=False,
            data='''{
  "programming": {
    "default_code": "# Implement this function:\\ndef is_odd(x: int) -> bool:\\n    pass\\n\\n# Example results:\\nprint(is_odd(1))  # True\\nprint(is_odd(2))  # False\\nprint(is_odd(3))  # True\\nprint(is_odd(4))  # False\\nprint(is_odd(5))  # True\\n",
    "version": "2.0",
    "merge_script": "data/modules/2/merge",
    "stdin": "data/modules/2/stdin.txt",
    "check_script": "data/modules/2/eval"
  }
}'''
        )
        session.add(programming_module)

        # Create Active Org
        active_org = ActiveOrg(
            org=1,
            year=1
        )
        session.add(active_org)

        # Create User Notify
        user_notify = UserNotify(
            user=1,
            auth_token='a4bcf1a180d5cd5a3e1a6d04df757537652f5448',
            notify_eval=True,
            notify_response=True,
            notify_ksi=True,
            notify_events=True
        )
        session.add(user_notify)

        # Create Config entries
        config_entries = [
            ('backend_url', 'http://localhost:3030', False),
            ('discord_invite_link', None, False),
            ('github_api_org_url', None, False),
            ('github_token', None, True),
            ('ksi_conf', 'all-organizers-group@localhost', False),
            ('mail_sender', None, False),
            ('mail_sign', 'Good luck!<br>Testing Seminar of Informatics', False),
            ('monitoring_dashboard_url', None, False),
            ('return_path', 'mail-error@localhost', False),
            ('seminar_repo', 'seminar', False),
            ('successful_participant_trophy_id', '-1', False),
            ('successful_participant_percentage', '60', False),
            ('webhook_discord_username_change', None, False),
            ('web_url_admin', None, False),
        ]

        for key, value, secret in config_entries:
            config_entry = Config(
                key=key,
                value=value,
                secret=secret
            )
            session.add(config_entry)

        # Check if task has deploy_date and deploy_status attributes
        if hasattr(Task, 'deploy_date'):
            first_task.deploy_date = datetime.datetime(2024, 8, 10, 16, 22, 5, 637466)
        if hasattr(Task, 'deploy_status'):
            first_task.deploy_status = 'done'
        if hasattr(Task, 'eval_comment'):
            first_task.eval_comment = ''

        # Commit all changes
        session.commit()

    except Exception as e:
        session.rollback()
        print(f"Error initializing development data: {e}")
        raise
    finally:
        session.close()


if __name__ == '__main__':
    init_dev_data()
