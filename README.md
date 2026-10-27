# Mileage Challenge World Ranking
This is an **UNOFFICIAL** on-track world ranking for Mileage Challenge teams which is inspired by the world ranking for Formula Student teams. The idea is to bridge the gap between regions and eventually competitions. Right now we are focusing solely on Shell Eco-marathon as they have an easy to access dataset.

This is a completely unofficial ranking and has nothing to do with the actual Shell eco-marathon championship points system or the World Final, my idea is to make a more ideal version of Shell's points system, which was only per event. Also shows consistency clearer so even if a team like for example Microjoule finished 4th this year, they are still ranked #1 because they finished first both years prior.

One thing I would love to do in the future is to bridge the results from other competitions outside of shell eco-marathon, for example the Pisaralla Pisimmälle or the Honda Eco-marathon.

If you have any suggestions please send them over! I'd gladly make changes if my system were to be unoptimal. Right now it is pretty apathetic towards track differences, which is unfair to teams with way tougher tracks.


## How does the ranking work?

My brain cooked this up at 11 pm on exam week, so it is far from perfect and very simple.

Teams are based on their Team ID and nothing else. If your team has kept the same Team ID but competed in different classes, it will be counted as the same team, and past scores in those in those past seasons will be kept.

If you compete in 2 events in a year, the event with the best points result will be kept, and the other thrown out.

The calculations are based on the Championship points system that Shell had set up for the 2026 season.

No points given for tech inspection, nor taken away for late tech inspection. If you did not complete a run or tech for an event you are given 0 points for that event.

First we calculate the on-track performance $S_{ontrack}$. Instead of taking the average of the 2 best attempts I prefer to use the one best attempt.

$$S_{ontrack} = 100 \cdot \frac{E_{teambest}}{E_{eventmax}}$$

We then calculated a competitiveness factor $C_k$, which is per event. This does not factor in track differences yet, so it may punish hillier tracks, or competition in lesser conditions

$$C_k = \frac{E_{eventmax}}{E_{worldmax}} $$

We then calculate the for that season $W_{points}$

$$W_{points} = S_{ontrack} \cdot C_k$$

Lastly $W_{points}$ is summed up per the last 3 years with the following weighting falloff, so newer seasons are worth more than older ones.

$$\{2026: 1.00, 2025: 0.65, 2024: 0.35\}$$

Then you finally get your point result! The absolute best points result possible is 200, and the worst being 0.



## Why no off-track award points?

I do not believe it to be fair to hand out points based on off-track awards since so few are given out per competition. It would basically hand the top ranking spots to one team per leaderboard. Unless we have something similar to the "Engineering Deisgn Event" at Formula Student Germany where each team is given points based on their design, it won't be considered. Also the data is annyoing to grab.