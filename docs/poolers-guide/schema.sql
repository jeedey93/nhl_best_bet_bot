-- Run this in the Supabase SQL editor

create table if not exists poolers_players (
  id        serial primary key,
  rank      int          not null,
  name      text         not null,
  team      text         not null,
  pos       text         not null,
  age       int,
  aav       numeric,
  pp_pct    numeric,
  last_gp   int,
  last_g    int,
  last_a    int,
  last_pts  int,
  proj_gp   int,
  proj_g    int,
  proj_a    int,
  proj_pts  int,
  tier      text,
  notes     text
);

-- Allow public read (for the guide page)
alter table poolers_players enable row level security;
create policy "Public read"   on poolers_players for select using (true);

-- Allow public write (anon key used by admin page)
-- If you want to restrict this, add an auth check instead of `true`
create policy "Public insert" on poolers_players for insert with check (true);
create policy "Public update" on poolers_players for update using (true);
create policy "Public delete" on poolers_players for delete using (true);

-- Seed data
insert into poolers_players (rank,name,team,pos,age,aav,pp_pct,last_gp,last_g,last_a,last_pts,proj_gp,proj_g,proj_a,proj_pts,tier,notes) values
(1,'Connor McDavid','EDM','C',29,12.5,92,82,64,93,157,82,62,89,151,'Elite','Generational ceiling'),
(2,'Leon Draisaitl','EDM','C',30,14.0,88,80,52,68,120,80,55,72,127,'Elite','Still elite even without McDavid linemates'),
(3,'Nathan MacKinnon','COL','C',31,12.6,90,76,45,69,114,79,50,75,125,'Elite','Avalanche push for Cup contention'),
(4,'Nikita Kucherov','TBL','RW',33,9.5,95,81,39,81,120,78,42,78,120,'Elite','PP maestro, age-related risk'),
(5,'Auston Matthews','TOR','C',29,13.25,75,68,49,36,85,75,58,47,105,'Elite','Injury history is the only concern'),
(6,'David Pastrnak','BOS','RW',30,11.25,82,82,46,47,93,81,52,50,102,'Top','Consistent 50-goal threat'),
(7,'Cale Makar','COL','D',27,9.0,88,77,24,62,86,80,28,68,96,'Top','Best D in the league'),
(8,'Mikko Rantanen','CAR','RW',29,13.0,80,81,42,47,89,82,44,51,95,'Top','New team, top-line role confirmed'),
(9,'Jason Robertson','DAL','LW',26,7.75,68,73,32,40,72,80,45,48,93,'Top','Bounce-back season expected'),
(10,'William Nylander','TOR','RW',30,11.5,72,82,37,45,82,82,40,50,90,'Top','Best value on the Leafs'),
(11,'Mitch Marner','TOR','RW',29,10.9,85,80,28,52,80,78,32,56,88,'Top','New contract, motivated'),
(12,'Sebastian Aho','CAR','C',28,8.45,70,82,34,44,78,82,38,48,86,'Top','Underrated every year'),
(13,'Elias Pettersson','VAN','C',27,11.6,78,72,26,38,64,75,36,48,84,'Top','Bounce-back after down year'),
(14,'Brayden Point','TBL','C',30,9.5,76,65,32,38,70,72,38,44,82,'Top','Injury risk, but elite when healthy'),
(15,'Jack Hughes','NJD','C',25,8.0,72,70,29,40,69,75,35,46,81,'Top','Team around him improving'),
(16,'Quinn Hughes','VAN','D',26,7.85,86,78,7,69,76,80,22,58,80,'Top','Top D2 pick value'),
(17,'Brady Tkachuk','OTT','LW',26,9.5,60,82,35,34,69,82,38,38,76,'Mid','Physical and consistent'),
(18,'Tage Thompson','BUF','C',27,7.14,65,78,38,29,67,79,42,33,75,'Mid','Volume shooter on bad team'),
(19,'Alex DeBrincat','DET','LW',28,9.5,70,82,36,28,64,80,40,33,73,'Mid','Goal scorer, weak team limits pts'),
(20,'Sam Reinhart','FLA','C',30,8.0,68,82,38,28,66,82,40,32,72,'Mid','Consistent but upside capped'),
(21,'Cole Caufield','MTL','RW',25,7.85,74,74,35,24,59,76,38,30,68,'Mid','Pure scorer, weak team'),
(22,'Trevor Zegras','ANA','C',25,5.0,55,58,14,24,38,72,28,38,66,'Sleeper','Health + development breakout candidate'),
(23,'Yegor Sharangovich','CGY','LW',27,5.25,48,79,30,24,54,78,32,28,60,'Sleeper','Quietly put up 30 last year'),
(24,'Logan Cooley','ARI','C',22,4.5,58,80,22,32,54,80,26,38,64,'Sleeper','Year 3 leap incoming'),
(25,'Matty Beniers','SEA','C',23,7.1,52,76,22,28,50,79,28,35,63,'Sleeper','Late-round gem, team improving');
