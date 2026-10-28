# Mileage Challenge World Ranking

This is an **UNOFFICIAL** on-track world ranking for Mileage Challenge teams which is inspired by the world ranking for Formula Student teams. The idea is to bridge the gap between regions and eventually competitions. Right now we are focusing solely on Shell Eco-marathon as they have an easy to access dataset.

This is a completely unofficial ranking and has nothing to do with the actual Shell eco-marathon championship points system or the World Final, my idea is to make a more ideal version of Shell's points system, which was only per event. Also shows consistency clearer so even if a team like for example Microjoule finished 4th this year, they are still ranked #1 because they finished first both years prior.

One thing I would love to do in the future is to bridge the results from other competitions outside of shell eco-marathon, for example the Pisaralla Pisimmälle or the Honda Eco-marathon.

If you have any suggestions please send them over! I'd gladly make changes if my system were to be unoptimal. Right now it is pretty apathetic towards track differences, which is unfair to teams with way tougher tracks.

## Is this ranking good?

Shortly, no. It doesn't really use anything like number of valid attempts, track differences, weather differences, and so on. All it really does is shows your score as a ratio of the global best score in your vehicle class over 3 years.

But it's fun! I wouldn't use this system as it is for invites to World Championship, but I like extending the competition across borders and seas.

## Should I use the SEM Scraper?

No, you will just get the same data I have included in the data folder and you will put unnecessary strain on Shell's servers. I just wanted the data source to be clear so it can be analyzed and critiqued.

## How does the ranking work?

Teams are identified by their Team ID. If your team has kept the same Team ID but competed in different classes, it will be counted as the same team, and past scores in those in those past seasons will be kept. Exceptions can be made and are listed in docs/exceptions.md
You can request exceptions either via DM or just via pull request.

If you compete in 2 events in a year, the event with the best points result will be kept, and the other thrown out.

No points given for tech inspection, nor taken away for late tech inspection. If you did not complete a single attempt or tech inspection in an event you are given 0 points for that event.

### Caluclations

The calculations are based on the Championship points system that Shell had set up for the 2026 season. First we calculate the on-track performance $S_{ontrack}$. Instead of taking the average of the 2 best attempts I prefer to use the one best attempt.

$$S_{ontrack} = 100 \cdot \frac{E_{teambest}}{E_{eventmax}}$$

We then calculate the for that year $W_{points}$

$$W_{points} = S_{ontrack} \cdot C_k$$

The Competitiveness Factor $C_k$ scales an event's points based on the quality of the podium field and the difficulty of the track.

$$C_k = \left(\; \text{Podium Ratio} \cdot M_{\text{track}}\right)$$

The Podium Ratio measures how the event's top teams compare to the global benchmark for that vehicle class and propulsion type.

**$E_{\text{event, top3}}$**: Average efficiency of the top 3 finishers at the event.  
**$E_{\text{world, top3}}$**: Average efficiency of the top 3 teams in the world that season.

$$\text{Podium Ratio} = \frac{E_{\text{event, top3}}}{E_{\text{world, top3}}}$$

The Podium Ratio rewards competing in more dominant regions.

Then a modifier per track is calculated. This is an attempt to reward teams with harder configurations, as not every track is created equal. Each track is compared to a baseline track of with a turn density of 4 turns/km, 2 m/km of elevation and average velocity of 25 km/h.

$$M_{\text{track}} = 1.0 + 0.08 \cdot \left(\frac{\text{turn\_density} - 4.0}{4.0}\right) + 0.06 \cdot \left(\frac{\text{elev\_rate} - 2.0}{2.0}\right) + 0.06 \cdot \left(\frac{v_{\text{avg}} - 25.0}{25.0}\right)$$

Where,

**$\text{turn\_density} = \frac{\text{turns} \times \text{laps}}{\text{total\_dist}}$** ($\text{turns/km}$), represenets cornering losses.

**$\text{elev\_rate} = \frac{\text{elevation\_change} \times \text{laps}}{\text{total\_dist}}$** ($\text{m/km}$), represents elevation change losses

**$v_{\text{avg}} = \frac{\text{total\_dist}}{\text{time} / 60}$** ($\text{km/h}$), represents rolling resistance losses

$M_{\text{track}}$ is clamped between 0.80 and 1.25. If track data is unavailable, $M_{\text{track}}$ defaults to 1. All track data is found in events.csv

Lastly $W_{points}$ is summed up per the last 3 years with the following weighting falloff, so newer seasons are worth more than older ones.

$$\{\text{Current Year}: 1.00, \text{1 Year Ago}: 0.65, \text{2 Years Ago}: 0.35\}$$

The theoretical best score for a single season is $100 * 1.25 = 125$, if you maintain a perfect score over 3 seasons in a completely dominant event with an extremely tough track. The theoretical highest world score is $125 \cdot (1 + 0.65 + 0.35) = 250$.

## Why no off-track award points?

I do not believe it to be fair to hand out points based on off-track awards since so few are given out per competition. It would basically hand the top ranking spots to one team per leaderboard. Unless we have something similar to the "Engineering Design Event" at Formula Student Germany where each team is given points based on their design, it won't be considered. Also the data is annyoing to grab.

## Was AI involved in this project?

Yes, helping with the frontend and the engine. Everything has been double-checked.
