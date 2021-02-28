import falcon
import json
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
            "Reply-To": String,
            "To": [year_id_1, year_id_2, ...] (resitelum v danych rocnicich),
            "Bcc": [String],
            "Gender": (both|male|female) - pokud neni vyplneno, je automaticky
                povazovano za "both",
            "KarlikSign": (true|false),
            "Easteregg": (true|false),
            "Successful": (true|false),
            "Category": ("hs", "other", "both"),
            "Type": ("ksi", "events"),
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
            if ('Successful' in data) and (data['Successful']):
                tos = {}
                for year in data['To']:
                    year_obj = session.query(model.Year).get(year)
                    tos.update({
                        user.id: user
                        for (user, _) in util.user.successful_participants(
                            year_obj
                        )
                    })

            else:
                tos = {
                    user.id: user
                    for user, year in util.user.active_years_all()
                    if user.role == 'participant' and year.id in data['To']
                }

                if ('Gender' in data) and (data['Gender'] != 'both'):
                    tos = {
                        user.id: user
                        for user in tos.values()
                        if user.sex == data['Gender']
                    }

            if 'Category' in data and data['Category'] != 'both':
                min_year = util.year.year_end(session.query(model.Year).
                                              get(min(data['To'])))
                max_year = util.year.year_end(session.query(model.Year).
                                              get(max(data['To'])))

                finish = {
                    id: year
                    for (id, year) in session.query(
                                        model.Profile.user_id,
                                        model.Profile.school_finish
                                      ).all()
                }

                if data['Category'] == 'hs':
                    tos = {
                        user.id: user
                        for user in tos.values()
                        if finish[user.id] >= min_year
                    }
                elif data['Category'] == 'other':
                    tos = {
                        user.id: user
                        for user in tos.values()
                        if finish[user.id] < max_year
                    }

            params = {}

            if 'Reply-To' in data and data['Reply-To']:
                params['Reply-To'] = data['Reply-To']

            body = data['Body']
            if ('KarlikSign' in data) and (data['KarlikSign']):
                body = body + util.config.karlik_img()
            if ('Easteregg' in data) and (data['Easteregg']):
                body = body + util.mail.easteregg()

            # Select notifications to build unsubscribes
            notifies = {
                n.user: n for n in session.query(model.UserNotify).all()
            }

            TYPE_MAPPING = {
                'ksi': util.mail.EMailType.KSI,
                'events': util.mail.EMailType.EVENTS,
            }

            message_type = (
                TYPE_MAPPING[data['Type']]
                if 'Type' in data and data['Type'] in TYPE_MAPPING
                else util.mail.EMailType.KSI
            )

            # Filter unsubscribed
            tos = {
                user_id: user
                for user_id, user in tos.items()
                if ((message_type == util.mail.EMailType.KSI and
                    notifies[user_id].notify_ksi) or
                    (message_type == util.mail.EMailType.EVENTS and
                     notifies[user_id].notify_events))
            }

            recipients = [
                util.mail.EMailRecipient(
                    user.email,
                    util.mail.Unsubscribe(
                        message_type,
                        notifies[user.id] if user.id in notifies else None,
                        user.id,
                        commit=False,  # we will commit new entries only once
                        backend_url=util.config.backend_url(),
                        ksi_web=util.config.ksi_web(),
                    )
                ) for user in tos.values()
            ]

            try:
                util.mail.send_multiple(
                    recipients,
                    data['Subject'],
                    body,
                    params,
                    data['Bcc'],
                )
                req.context['result'] = {'count': len(tos)}
                session.commit()
            except Exception as e:
                req.context['result'] = {'error': str(e)}
                resp.status = falcon.HTTP_500

        except SQLAlchemyError:
            session.rollback()
            raise
        finally:
            session.close()
