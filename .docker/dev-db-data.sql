BEGIN TRANSACTION;
INSERT INTO "years" ("id","year","sealed","point_pad") VALUES (1,'2024',0,0);
INSERT INTO "users" ("id","email","github","discord","phone","first_name","nick_name","last_name","sex","password","short_info","profile_picture","role","enabled","registered","last_logged_in") VALUES (1,'admin@localhost',NULL,NULL,NULL,'Admin','','Developer','male','$2b$12$8msl2crG4so1cwDiDeFkoeNTwnSLHSusmkbuNintOov0dLb9ihuKa','',NULL,'admin',1,'2000-01-01 00:00:00.000000','2024-08-10 15:43:25.227080');
INSERT INTO "tasks" ("id","title","author","co_author","wave","prerequisite","intro","body","solution","thread","picture_base","time_created","time_deadline","evaluation_public","git_path","git_branch","git_commit","git_pull_id","deploy_date","deploy_status","eval_comment") VALUES (1,'First Task Name',1,NULL,1,NULL,'This text is shown in a popup on hover.','<p>Content of the first task.</p>','<p>Solution.</p>
<h3 id="h2">H2</h3>
<p>More solution.</p>
',1,NULL,'2024-08-10 15:43:35.120071','2099-01-01 23:59:59.000000',0,'2024/vlna1/uloha_01_first_task','master','7bef31b57bb0d57167fb86a998218be35b74782b',NULL,'2024-08-10 16:22:05.637466','done','');
INSERT INTO "waves" ("id","year","index","caption","garant","time_published") VALUES (1,1,1,'First Wave',1,'2098-12-31 23:00:00.000000');
INSERT INTO "profiles" ("user_id","addr_street","addr_city","addr_zip","addr_country","school_name","school_street","school_city","school_zip","school_country","school_finish","tshirt_size","referral") VALUES (1,'Street 1','City','123','cz','Uni','Street Uni','City Uni','456','cz',2000,'NA',NULL);
INSERT INTO "articles" ("id","author","title","body","picture","time_created","published","year","resource") VALUES (1,1,'Welcome to the test site!','<p>This is a test site with a very simple testing content.</p>',NULL,'1999-12-31 23:00:00.000000',1,1,'articles/1');
INSERT INTO "threads" ("id","title","public","year") VALUES (1,'First Task Name',1,1);
INSERT INTO "modules" ("id","task","type","name","description","max_points","autocorrect","order","bonus","custom","action","data") VALUES (1,1,'general','File submission module','<p>Feel free to try it out</p>
',10,0,0,0,0,NULL,'{}'),
 (2,1,'programming','Programming module','<p>Your task is to write a function that check if a number is odd or even.</p>
',2,1,1,0,0,NULL,'{
  "programming": {
    "default_code": "# Implement this function:\ndef is_odd(x: int) -> bool:\n    pass\n\n# Example results:\nprint(is_odd(1))  # True\nprint(is_odd(2))  # False\nprint(is_odd(3))  # True\nprint(is_odd(4))  # False\nprint(is_odd(5))  # True\n",
    "version": "2.0",
    "merge_script": "data/modules/2/merge",
    "stdin": "data/modules/2/stdin.txt",
    "check_script": "data/modules/2/eval"
  }
}');
INSERT INTO "active_orgs" ("org","year") VALUES (1,1);
INSERT INTO "users_notify" ("user","auth_token","notify_eval","notify_response","notify_ksi","notify_events") VALUES (1,'a4bcf1a180d5cd5a3e1a6d04df757537652f5448',1,1,1,1);
INSERT INTO `config` (`key`, `value`, `secret`) VALUES
('backend_url', 'http://localhost:3030', 0),
('discord_invite_link', NULL, 0),
('github_api_org_url', NULL, 0),
('github_token', NULL, 1),
('ksi_conf', 'all-organizers-group@localhost', 0),
('mail_sender', NULL, 0),
('mail_sign', 'Good luck!<br>Testing Seminar of Informatics', 0),
('monitoring_dashboard_url', NULL, 0),
('return_path', 'mail-error@localhost', 0),
('seminar_repo', 'seminar', 0),
('successful_participant_trophy_id', NULL, 0),
('successful_participant_percentage', '60', 0),
('webhook_discord_username_change', NULL, 0),
('web_url_admin', NULL, 0),
('mail_subject_prefix', '[TEST SEMINAR]', 0),
('seminar_name', 'Testing Seminar of Informatics', 0),
('seminar_name_short', 'TSI', 0),
('mail_registration_welcome', 'testing seminar of informatics.', 0),
('box_prefix_id', '1', 0),
('web_url', 'http://localhost:8080', 0);
COMMIT;
