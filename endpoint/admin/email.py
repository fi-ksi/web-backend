import falcon
import json
from sqlalchemy import func
from sqlalchemy.exc import SQLAlchemyError

from db import session
import model
import util


class Email(object):

    def on_post(self, req, resp):
        """
        Specifikace POST pozadavku:
        {
            "Subject": String,
            "Body": String,
            "Sender": String,
            "Reply-To": String,
            "To": [] | [year_id_1, year_id_2, ...] (bud vsem resitelum, nebo
                resitelum v danych rocnicich),
            "Bcc": [String],
            "Gender": (both|male|female) - pokud neni vyplneno, je automaticky
                povazovano za "both",
            "KarlikSign": (true|false),
            "Easteregg": (true|false),
            "Successful": (true|false)
        }

        Backend edpovida:
        {
            count: Integer
        }

        """

        try:
            user = req.context['user']

            if (not user.is_logged_in()) or (not user.is_org()):
                resp.status = falcon.HTTP_400
                return

            data = json.loads(req.stream.read().decode('utf-8'))['e-mail']

            # Filtrovani uzivatelu
            if data['To'] != []:
                active = util.user.active_years_all()
                active = [
                    user
                    for (user, year) in [
                        user_year
                        for user_year in active
                        if (user_year[0].role == 'participant' and
                            user_year[1].id in data['To'])
                    ]
                ]
                if ('Gender' in data) and (data['Gender'] != 'both'):
                    active = [
                        user for user in active if user.sex == data['Gender']
                    ]
                to = active
            else:
                query = session.query(model.User).\
                    filter(model.User.role == 'participant')
                if ('Gender' in data) and (data['Gender'] != 'both'):
                    query = query.filter(model.User.sex == data['Gender'])
                to = query.all()

            if ("Successful" in data) and (data['Successful']):
                succ = set()
                for year in data['To']:
                    year_obj = session.query(model.Year).get(year)
                    succ |= set([
                        user_points[0].id
                        for user_points in util.user.successful_participants(
                            year_obj
                        )
                    ])
                to = [user for user in to if user.id in succ]

            to = set([user.email for user in to])

            params = {
                'Reply-To': data['Reply-To'],
                'Sender': data['Sender']
            }

            body = data['Body']
            if ('KarlikSign' in data) and (data['KarlikSign']):
                body = body + util.config.karlik_img()
            if ('Easteregg' in data) and (data['Easteregg']):
                body = body + util.mail.easteregg()

            try:
                util.mail.send_multiple(
                    to,
                    data['Subject'],
                    body, params,
                    data['Bcc']
                )
                req.context['result'] = {'count': len(to)}
            except Exception as e:
                req.context['result'] = {'error': str(e)}
                resp.status = falcon.HTTP_500

        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
