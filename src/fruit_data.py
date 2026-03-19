# fruit_data.py 
# Static pruning knowledge base for fruit trees and bushes. 
# Each species has a list of tasks with timing windows and guidance. 

FRUIT_SPECIES = { 
    "Apple": { 
        "icon": "🍎", 
        "description": "Prune during winter dormancy. Fruits on spurs and 2-year wood.", 
        "tasks": [ 
            { 
                "key": "apple_winter_prune", 
                "name": "Winter Renovation Prune", 
                "months": [2, 3],          # February–March 
                "month_label": "Feb – Mar", 
                "type": "Annual", 
                "urgency": "high", 
                "guidance": ( 
                    "Prune during full dormancy, before buds break. " 
                    "Remove dead, diseased, damaged, and crossing branches first (the 4 Ds). " 
                    "Aim for an open goblet/vase shape — light must reach the centre. " 
                    "Cut back to a strong outward-facing lateral at least ⅓ the diameter of the removed branch. " 
                    "Never remove more than 25–30% of the crown in a single year. " 
                    "Check buds: tight and hard = fine to prune. Green tip visible = prune immediately or wait until next year." 
                ), 
                "tool_tip": "Sharp secateurs up to 1.5 cm, loppers up to 4 cm, pruning saw for larger cuts.", 
            }, 
            { 
                "key": "apple_summer_tidy", 
                "name": "Summer Tidy — Water Shoots", 
                "months": [6, 7], 
                "month_label": "Jun – Jul", 
                "type": "Optional", 
                "urgency": "low", 
                "guidance": ( 
                    "Remove any vigorous vertical water shoots (Wassertriebe) that appeared after winter pruning. " 
                    "These are thin, perfectly upright shoots that will never fruit and shade productive wood. " 
                    "Rub off small ones by hand if caught early; cut flush for larger ones. " 
                    "This is also a good time to thin fruit clusters if the tree is overloaded — " 
                    "aim for one fruit per spur, spaced 10–15 cm apart, to get larger individual fruits." 
                ), 
                "tool_tip": "Secateurs or fingers for young water shoots.", 
            }, 
        ] 
    }, 

    "Mirabelle": { 
        "icon": "🟡", 
        "description": "Prunes like apple — winter dormancy. Fruits on 1 and 2-year wood.", 
        "tasks": [ 
            { 
                "key": "mirabelle_winter_prune", 
                "name": "Winter Renovation Prune", 
                "months": [2, 3], 
                "month_label": "Feb – Mar", 
                "type": "Annual", 
                "urgency": "high", 
                "guidance": ( 
                    "Prune in late February to mid-March while fully dormant. " 
                    "Mirabelles fruit on both 1 and 2-year-old laterals, so preserve a good proportion of younger wood. " 
                    "Thin out older framework branches gradually over 2–3 years if the tree is congested — " 
                    "this stimulates fresh, productive growth from the base. " 
                    "Same 25–30% maximum removal rule applies. " 
                    "Aim for an open centre with well-spaced main branches." 
                ), 
                "tool_tip": "Sterilise tools before use — wipe blades with isopropyl alcohol between trees.", 
            }, 
            { 
                "key": "mirabelle_fruit_thin", 
                "name": "Fruit Thinning", 
                "months": [5, 6], 
                "month_label": "May – Jun", 
                "type": "Optional", 
                "urgency": "low", 
                "guidance": ( 
                    "After natural fruit drop (June drop), thin remaining fruitlets to 5–7 cm spacing. " 
                    "This prevents biennial bearing (alternating heavy and light crop years) " 
                    "and improves the size and quality of individual fruits. " 
                    "Remove any damaged, misshapen, or pest-affected fruitlets first." 
                ), 
                "tool_tip": "Fingers or small scissors. Do not pull — twist and lift.", 
            }, 
        ] 
    }, 

    "Cherry": { 
        "icon": "🍒", 
        "description": "Summer prune ONLY — winter pruning risks silver leaf disease and bacterial canker.", 
        "tasks": [ 
            { 
                "key": "cherry_summer_prune", 
                "name": "Summer Prune (Post-Harvest)", 
                "months": [7, 8], 
                "month_label": "Jul – Aug", 
                "type": "Annual", 
                "urgency": "high", 
                "guidance": ( 
                    "⚠️ Never prune cherries in winter or wet conditions — high risk of silver leaf fungal disease " 
                    "(Bleiglanzerkrankheit) and bacterial canker entering through cuts. " 
                    "Prune only in dry summer weather, ideally July–August after fruiting is complete. " 
                    "Dry conditions allow wounds to seal rapidly, minimising infection risk. " 
                    "Remove crossing, crowded, and inward-growing branches. " 
                    "Seal all cuts over 3–4 cm diameter immediately with wound sealant (Wundverschlussmittel). " 
                    "Use a sharp pruning saw — clean cuts seal faster than crushed cuts from blunt tools. " 
                    "Sterilise tools with isopropyl alcohol before starting and between cuts on diseased wood." 
                ), 
                "tool_tip": "Sharp saw essential. Wound sealant ready before you start cutting.", 
            }, 
            { 
                "key": "cherry_disease_check", 
                "name": "Disease & Silver Leaf Check", 
                "months": [4, 5], 
                "month_label": "Apr – May", 
                "type": "Annual", 
                "urgency": "medium", 
                "guidance": ( 
                    "Inspect foliage as it emerges for signs of silver leaf disease: " 
                    "leaves with a metallic silvery sheen on upper surface, often on one branch first. " 
                    "Also check for bacterial canker: sunken, dead patches of bark with amber gum oozing. " 
                    "If silver leaf is confirmed, remove affected branches 15 cm below the last point of internal brown staining " 
                    "(cut and check the cut surface — healthy wood is white, infected wood shows brown staining). " 
                    "Burn or bin affected wood — do not compost." 
                ), 
                "tool_tip": "Check cut surfaces for brown staining when diagnosing silver leaf.", 
            }, 
        ] 
    }, 

    "Red Currant": { 
        "icon": "🔴", 
        "description": "Fruits on short spurs on older wood and at base of 1-year shoots.", 
        "tasks": [ 
            { 
                "key": "redcurrant_winter_prune", 
                "name": "Winter Prune", 
                "months": [11, 12, 1, 2], 
                "month_label": "Nov – Feb", 
                "type": "Annual", 
                "urgency": "high", 
                "guidance": ( 
                    "Red currants fruit on spurs growing from older wood and at the base of last year's shoots. " 
                    "Goal: maintain a permanent framework of 8–10 main branches of mixed ages. " 
                    "Each winter, remove 1–2 of the oldest (darkest, woodiest) branches entirely at the base " 
                    "to encourage vigorous replacement shoots. " 
                    "Shorten all sideshoots to 1–2 buds from their base to build up fruiting spurs. " 
                    "Keep the centre open and remove any shoots growing inward or crossing. " 
                    "Aim for a goblet shape on a short leg (10–15 cm clear stem at the base)." 
                ), 
                "tool_tip": "Secateurs for most cuts. The oldest wood is easy to identify — it's the darkest and most gnarled.", 
            }, 
            { 
                "key": "redcurrant_summer_pinch", 
                "name": "Summer Shoot Pinch", 
                "months": [6, 7], 
                "month_label": "Jun – Jul", 
                "type": "Optional", 
                "urgency": "low", 
                "guidance": ( 
                    "Pinch out the tips of new sideshoots to 5 leaves from their base. " 
                    "This redirects energy into the developing fruit clusters and improves air circulation, " 
                    "reducing the risk of powdery mildew and botrytis in a wet summer. " 
                    "Do not shorten the main branch leaders — let those grow freely until winter." 
                ), 
                "tool_tip": "Fingers or sharp secateurs. Quick job once you get the eye for it.", 
            }, 
        ] 
    }, 

    "Raspberry": { 
        "icon": "🫐", 
        "description": "Summer vs autumn varieties have opposite pruning logic — identify your type first.", 
        "tasks": [ 
            { 
                "key": "raspberry_identify", 
                "name": "Identify Variety Type", 
                "months": [7, 8, 9, 10], 
                "month_label": "Jul – Oct (first year)", 
                "type": "One-off", 
                "urgency": "medium", 
                "guidance": ( 
                    "This determines all future pruning. " 
                    "Summer-fruiting raspberries: fruit in June–July on canes grown the previous year. " 
                    "Autumn-fruiting raspberries: fruit August–October on canes grown this same year. " 
                    "If you are unsure: watch when your canes fruit for one season, then you will know." 
                ), 
                "tool_tip": "Summer fruiters have two distinct cane generations visible. Autumn fruiters fruit on young green canes.", 
            }, 
            { 
                "key": "raspberry_summer_postcrop", 
                "name": "Post-Harvest Prune (Summer Varieties)", 
                "months": [7, 8], 
                "month_label": "Jul – Aug (after fruiting)", 
                "type": "Annual", 
                "urgency": "high", 
                "guidance": ( 
                    "For summer-fruiting varieties only. " 
                    "Immediately after harvest, cut all canes that just fruited (the darker, woodier ones) " 
                    "down to ground level — these will never fruit again. " 
                    "Leave all the new green canes that grew this year — these will fruit next summer. " 
                    "Thin new canes to 8–10 per metre of row, keeping the strongest and most upright. " 
                    "Tie remaining canes to wires or supports." 
                ), 
                "tool_tip": "Fruited canes are easily distinguished — darker, woody, and have small dried fruit stalks attached.", 
            }, 
            { 
                "key": "raspberry_autumn_postcrop", 
                "name": "Post-Harvest Prune (Autumn Varieties)", 
                "months": [2, 3], 
                "month_label": "Feb – Mar", 
                "type": "Annual", 
                "urgency": "high", 
                "guidance": ( 
                    "For autumn-fruiting varieties only. " 
                    "In late winter, cut ALL canes down to ground level — every single one. " 
                    "This sounds drastic but is correct: new canes will grow from the base in spring " 
                    "and fruit on their tips in autumn of the same year. " 
                    "No thinning needed at this stage — thin to 8–10 per metre once new canes reach 30 cm." 
                ), 
                "tool_tip": "Cut everything — no need to distinguish cane ages for autumn varieties.", 
            }, 
        ] 
    }, 

    "Blackberry": { 
        "icon": "🫐", 
        "description": "Like raspberries, fruits on previous year's canes. Vigorous — needs firm management.", 
        "tasks": [ 
            { 
                "key": "blackberry_postcrop", 
                "name": "Post-Harvest Prune", 
                "months": [9, 10], 
                "month_label": "Sep – Oct (after fruiting)", 
                "type": "Annual", 
                "urgency": "high", 
                "guidance": ( 
                    "Immediately after fruiting is complete, cut all canes that fruited this year " 
                    "down to ground level. These are the older, woodier canes. " 
                    "Retain all new canes that grew this year (greener, more flexible) — " 
                    "these will fruit next season. " 
                    "Blackberries are vigorous and will produce many new canes — " 
                    "select the 5–8 strongest and remove the rest entirely. " 
                    "Tie selected canes to wires in a fan or weave pattern." 
                ), 
                "tool_tip": "Thick gloves essential — even thornless varieties can scratch. Long-handled loppers help with older woody canes.", 
            }, 
            { 
                "key": "blackberry_tip_prune", 
                "name": "New Cane Tip Pruning", 
                "months": [6, 7], 
                "month_label": "Jun – Jul", 
                "type": "Annual", 
                "urgency": "medium", 
                "guidance": ( 
                    "When new canes reach approximately 180 cm, pinch or cut out the growing tip. " 
                    "This encourages branching lower down the cane, which increases the number of " 
                    "fruiting laterals next year and keeps growth manageable. " 
                    "Without this step, blackberries produce very long whippy canes that are hard to manage " 
                    "and fruit only at the very tips." 
                ), 
                "tool_tip": "Secateurs or fingers. Do this while canes are still green and soft — much easier than waiting.", 
            }, 
        ] 
    }, 
} 

def get_due_tasks(species_name, month): 
    """Return list of tasks due in a given month for a species.""" 
    species = FRUIT_SPECIES.get(species_name) 
    if not species: 
         return [] 
    return [t for t in species["tasks"] if month in t["months"]] 

def get_urgency_color(urgency): 
    """Return a colour string for urgency level.""" 
    return {"high": "🔴", "medium": "🟡", "low": "🟢"}.get(urgency, "⚪") 
