import streamlit as st
from database import create_db_and_tables, seed_data, SessionLocal, CropTemplate, Cultivation, get_db
from crud import (
    create_template, get_templates, update_template, delete_template,
    start_cultivation, get_cultivations, update_cultivation, delete_cultivation,
    get_template_by_id, get_cultivation_by_id,
    create_yield, get_yields, get_yield_by_id, get_yields_by_cultivation, get_yields_by_crop, update_yield, delete_yield
)
import os
import datetime
import pandas as pd
import plotly.express as px
from fruit_data import FRUIT_SPECIES, get_due_tasks, get_urgency_color 
from crud_fruit import ( 
    add_fruit_plant, get_fruit_plants, delete_fruit_plant, 
    log_pruning, get_pruning_logs_for_plant, delete_pruning_log 
)

# Configure page layout and styling
st.set_page_config(layout="wide", page_title="Crop Tracker", initial_sidebar_state="expanded")

# Custom CSS for improved styling
st.markdown("""
    <style>
        .metric-card {
            background-color: #f0f2f6;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #FF6B6B;
        }
        .success-card {
            background-color: #d4edda;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #28a745;
        }
        .warning-card {
            background-color: #fff3cd;
            padding: 15px;
            border-radius: 8px;
            border-left: 4px solid #ffc107;
        }
        .help-text {
            font-size: 12px;
            color: #666;
            margin-top: 5px;
            font-style: italic;
        }
        h1 {
            color: #2d5020;
            border-bottom: 3px solid #FF6B6B;
            padding-bottom: 10px;
        }
        h2 {
            color: #2d5020;
            margin-top: 20px;
        }
    </style>
    """, unsafe_allow_html=True)

st.title("🌱 Crop Tracker")
st.markdown("*Track your home garden's growth, yields, and performance year over year*")

# Initialize database and seed data if not already done
# For PostgreSQL/Supabase, we rely on create_db_and_tables to be safe
try:
    # Always try to create tables if they don't exist
    create_db_and_tables()
    
    # Check if we should seed (only if it's a fresh DB)
    db_init = next(get_db())
    if not get_templates(db_init):
        seed_data(db_init)
        st.success("✅ Database initialized with Crop Registry templates!")
    db_init.close()
except Exception as e:
    # Don't halt the app if seeding fails, but log it
    print(f"Database initialization info: {e}")

st.sidebar.header("📍 Navigation")
st.sidebar.markdown("---")

# Use session state to handle page navigation without widget key conflicts
if 'nav_choice' not in st.session_state:
    st.session_state.nav_choice = "Dashboard"

# We use index based on session state to avoid the "cannot be modified after instantiation" error
page_list = ["Dashboard", "Timeline", "Crop Registry", "Active Cultivations", "Yield Tracker", "Fruit and Pruning"]
current_index = page_list.index(st.session_state.nav_choice)

page = st.sidebar.radio("Go to", page_list, index=current_index, label_visibility="collapsed")

# Update session state if user clicks a different radio button
if page != st.session_state.nav_choice:
    st.session_state.nav_choice = page
    st.rerun()

db = next(get_db())

# Helper function to show progress bar for cultivation
def get_cultivation_progress(cultivation):
    """Calculate cultivation progress as percentage"""
    today = datetime.date.today()
    if cultivation.predicted_last_harvest_date:
        total_days = (cultivation.predicted_last_harvest_date - cultivation.sow_date).days
        days_elapsed = (today - cultivation.sow_date).days
        progress = min(100, max(0, (days_elapsed / total_days * 100) if total_days > 0 else 0))
        return progress
    return 0

# Helper function to get stage of cultivation
def get_cultivation_stage(cultivation):
    """Determine current stage of cultivation"""
    today = datetime.date.today()
    if cultivation.actual_transplant_date or (cultivation.predicted_transplant_date and today >= cultivation.predicted_transplant_date):
        return "🌿 Transplanted"
    elif cultivation.actual_germination_date or (cultivation.predicted_germination_date and today >= cultivation.predicted_germination_date):
        return "🌱 Germinated"
    else:
        return "🥀 Sowing"

if page == "Dashboard":
    st.header("📊 Weekly Dashboard")
    
    col_info = st.columns([1, 1])
    with col_info[0]:
        st.markdown("<p class='help-text'>ℹ️ Get a quick overview of what to do this week in your garden</p>", unsafe_allow_html=True)
    
    # Start Seeding/Germination Feature
    st.subheader("🌾 Start Seeding / Germination")
    templates = get_templates(db)
    # Sort templates alphabetically by name
    templates = sorted(templates, key=lambda x: (x.name.lower(), (x.variety or "").lower()))
    
    # Pre-populate template options and add a redirect option
    template_options = {f"{t.name}{' (' + t.variety + ')' if t.variety else ''}": t.id for t in templates}
    options = list(template_options.keys()) + ["+ Add New Crop to Registry"]
    
    # Default to "+ Add New Crop to Registry" (the last index)
    selected_option = st.selectbox("Choose a crop from Registry", options=options, index=len(options)-1, help="Select a crop template to start cultivation")
    
    if selected_option == "+ Add New Crop to Registry":
        if st.button("Go to Crop Registry"):
            st.session_state.nav_choice = "Crop Registry"
            st.rerun()
    else:
        sow_date = st.date_input("Sowing Date", datetime.date.today(), help="Date when you will sow the seeds")
        
        if st.button("Start Cultivation", type="primary"):
            if templates and selected_option in template_options:
                template_id = template_options[selected_option]
                start_cultivation(db, template_id, sow_date)
                st.success(f"✅ Started cultivation for {selected_option}!")
                st.rerun()
            else:
                st.error("Please select a valid crop or add one to the Registry.")

    # Dashboard Status
    st.divider()
    cultivations = get_cultivations(db)
    # Sort cultivations alphabetically by template name
    cultivations = sorted(cultivations, key=lambda x: (x.template.name.lower(), (x.template.variety or "").lower()))
    
    if not cultivations:
        st.info("🌍 No crops in cultivation. Start one above!")
    else:
        today = datetime.date.today()
        one_week_ago = today - datetime.timedelta(days=7)
        one_week_from_now = today + datetime.timedelta(days=7)

        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🆕 Recently Sown (Last 7 Days)")
            recently_sown = [c for c in cultivations if c.sow_date >= one_week_ago and c.sow_date <= today]
            if recently_sown:
                for c in recently_sown:
                    st.write(f"- **{c.template.name}**{' (' + c.template.variety + ')' if c.template.variety else ''} sown on {c.sow_date}")
            else:
                st.write("None")

            st.subheader("✄️ Needs Pricking Out")
            st.markdown(
                "<p class='help-text'>Seedlings ready to be moved into individual pots. "
                "Prick out when the first TRUE leaves are well developed (not the round seed leaves/cotyledons). "
                "Handle by the seed leaf, never by the stem — a damaged stem is fatal, a damaged seed leaf is not.</p>",
                unsafe_allow_html=True
            )
            needs_pricking = [
                c for c in cultivations
                if c.predicted_germination_date and c.predicted_germination_date <= today
                and (not c.predicted_transplant_date or c.predicted_transplant_date > today)
                and not c.actual_transplant_date
            ]
            if needs_pricking:
                for c in needs_pricking:
                    st.write(f"- **{c.template.name}** - Germinated around {c.predicted_germination_date}")
            else:
                st.write("None")

        with col2:
            st.subheader("🚀 Needs Transplanting (Next 7 Days)")
            st.markdown("<p class='help-text'>Move seedlings to final location</p>", unsafe_allow_html=True)
            needs_transplanting = [
                c for c in cultivations
                if c.predicted_transplant_date and c.predicted_transplant_date >= today
                and c.predicted_transplant_date <= one_week_from_now
                and not c.actual_transplant_date
            ]
            if needs_transplanting:
                for c in needs_transplanting:
                    st.write(f"- **{c.template.name}** - Predicted: {c.predicted_transplant_date}")
            else:
                st.write("None")

            st.subheader("🥗 Currently Harvestable")
            harvestable = [
                c for c in cultivations
                if c.predicted_first_harvest_date and c.predicted_first_harvest_date <= today
                and (not c.predicted_last_harvest_date or c.predicted_last_harvest_date >= today)
            ]
            if harvestable:
                for c in harvestable:
                    st.write(f"- **{c.template.name}** - Harvest window started {c.predicted_first_harvest_date}")
            else:
                st.write("None")

elif page == "Timeline":
    st.header("📈 Active Cultivations Timeline")
    st.markdown("<p class='help-text'>ℹ️ Visualize all your cultivations on a timeline showing germination, transplant, and harvest phases</p>", unsafe_allow_html=True)
    
    cultivations = get_cultivations(db)
    # Sort cultivations alphabetically for timeline
    cultivations = sorted(cultivations, key=lambda x: (x.template.name.lower(), (x.template.variety or "").lower()))

    if not cultivations:
        st.info("No crops in cultivation to display.")
    else:
        timeline_data = []
        for c in cultivations:
            variety_str = f" ({c.template.variety})" if c.template.variety else ""
            label = f"{c.template.name}{variety_str} [Sown: {c.sow_date}]"
            
            if c.predicted_germination_date:
                timeline_data.append(dict(Task=label, Start=c.sow_date, Finish=c.predicted_germination_date, Resource="Germination"))
            
            if c.predicted_transplant_date:
                timeline_data.append(dict(Task=label, Start=c.sow_date, Finish=c.predicted_transplant_date, Resource="Transplant"))
            
            if c.predicted_first_harvest_date:
                finish = c.predicted_last_harvest_date if c.predicted_last_harvest_date else c.predicted_first_harvest_date + datetime.timedelta(days=14)
                timeline_data.append(dict(Task=label, Start=c.predicted_first_harvest_date, Finish=finish, Resource="Harvest"))

        if timeline_data:
            df = pd.DataFrame(timeline_data)
            fig = px.timeline(df, x_start="Start", x_end="Finish", y="Task", color="Resource",
                            color_discrete_map={"Germination": "#3498db", "Transplant": "#f39c12", "Harvest": "#27ae60"})
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("Not enough data for timeline.")

elif page == "Crop Registry":
    st.header("🌿 Crop Registry (Templates)")
    st.markdown("<p class='help-text'>ℹ️ Manage your crop templates. Add new crop types and varieties with expected growth timelines</p>", unsafe_allow_html=True)
    
    with st.expander("➕ Add New Template", expanded=False):
        templates = get_templates(db)
        base_crop_names = sorted(list(set(t.name for t in templates)))
        
        mode = st.radio("Add Mode", ["New Base Crop", "New Variety of Existing Crop"], horizontal=True)
        
        # Determine initial values for cloning if in variety mode
        clone_template = None
        if mode == "New Variety of Existing Crop" and base_crop_names:
            base_name = st.selectbox("Select Base Crop", base_crop_names)
            # Find the first template with this name to clone its settings
            clone_template = next((t for t in templates if t.name == base_name), None)

        with st.form("new_template_form"):
            if mode == "New Base Crop":
                name = st.text_input("Crop Name (e.g. Tomato)")
                variety = st.text_input("Variety (e.g. Cherry - optional)")
            else:
                # Variety mode: lock the name, focus on variety
                name = st.text_input("Base Crop Name", value=clone_template.name if clone_template else "", disabled=True)
                variety = st.text_input("Variety Name (e.g. Cherry)")
            
            # Form fields pre-filled from clone_template if available
            # We map variations like "Indoors" or "Indoors " to the standard "Indoor"
            loc_options = ["Indoor", "Direct Outdoor", "Grow Bag"]
            def map_loc(loc):
                if not loc: return 0
                l = loc.strip().lower()
                if "indoor" in l: return 0
                if "direct" in l: return 1
                if "grow" in l: return 2
                return 0

            sow_location = st.selectbox("Sow Location", loc_options, 
                                       index=map_loc(clone_template.sow_location) if clone_template else 0,
                                       help="Where you will sow the seeds: indoors (e.g. seed tray), direct outdoor, or grow bag")
            
            expected_germ = st.number_input("Days to Germination", min_value=0, 
                                           value=clone_template.expected_days_to_germination if clone_template else 7,
                                           help="Expected days until seedlings emerge")
            expected_trans = st.number_input("Days to Transplant", min_value=0, 
                                            value=clone_template.expected_days_to_transplant if clone_template else 30,
                                            help="Days until ready to move to larger container or final location")
            expected_harvest_start = st.number_input("Days to First Harvest", min_value=0, 
                                                    value=clone_template.expected_days_to_first_harvest if clone_template else 60,
                                                    help="Days until first harvest is ready")
            expected_harvest_end = st.number_input("Days to Last Harvest", min_value=0, 
                                                  value=clone_template.expected_days_to_last_harvest if clone_template else 90,
                                                  help="Days until harvest window ends")
            notes = st.text_area("Notes", value=clone_template.notes if clone_template else "", help="Any additional notes about growing this crop")
            
            if st.form_submit_button("Add to Registry", type="primary"):
                if mode == "New Variety of Existing Crop" and not variety:
                    st.error("Please provide a variety name.")
                elif mode == "New Base Crop" and not name:
                    st.error("Please provide a crop name.")
                else:
                    final_name = clone_template.name if mode == "New Variety of Existing Crop" else name
                    create_template(db, {
                        "name": final_name, "variety": variety, "sow_location": sow_location,
                        "expected_days_to_germination": expected_germ,
                        "expected_days_to_transplant": expected_trans,
                        "expected_days_to_first_harvest": expected_harvest_start,
                        "expected_days_to_last_harvest": expected_harvest_end,
                        "notes": notes
                    })
                    st.success(f"✅ Added {final_name} {variety if variety else ''} to Registry!")
                    st.rerun()

    st.divider()
    st.subheader("📚 Registry Templates")
    templates = get_templates(db)
    # Sort templates alphabetically
    templates = sorted(templates, key=lambda x: (x.name.lower(), (x.variety or "").lower()))
    
    if not templates:
        st.info("No templates found.")
    else:
        for t in templates:
            variety_str = f" ({t.variety})" if t.variety else ""
            with st.expander(f"🌾 {t.name}{variety_str}"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write(f"**📍 Location:** {t.sow_location}")
                    st.write(f"**🌱 Germination:** {t.expected_days_to_germination}d")
                    st.write(f"**🚀 Transplant:** {t.expected_days_to_transplant}d")
                with col2:
                    st.write(f"**🥗 First Harvest:** {t.expected_days_to_first_harvest}d")
                    st.write(f"**📦 Last Harvest:** {t.expected_days_to_last_harvest}d")
                if t.notes:
                    st.markdown(f"**📝 Notes:** {t.notes}")
                if st.button(f"Delete {t.name}{variety_str}", key=f"del_t_{t.id}", use_container_width=True):
                    delete_template(db, t.id)
                    st.rerun()

elif page == "Active Cultivations":
    st.header("🌾 Active Cultivations")
    st.markdown("<p class='help-text'>ℹ️ Track the progress of your current cultivations. Update actual dates and log yields when ready</p>", unsafe_allow_html=True)
    
    cultivations = get_cultivations(db)
    # Sort cultivations alphabetically
    cultivations = sorted(cultivations, key=lambda x: (x.template.name.lower(), (x.template.variety or "").lower()))
    
    if not cultivations:
        st.info("No crops in cultivation.")
    else:
        for c in cultivations:
            variety_str = f" ({c.template.variety})" if c.template.variety else ""
            progress = get_cultivation_progress(c)
            stage = get_cultivation_stage(c)
            
            with st.expander(f"{c.template.name}{variety_str} - Sown: {c.sow_date} | {stage}", expanded=False):
                # Progress bar
                st.progress(progress / 100, text=f"Progress: {progress:.0f}%")
                
                st.write("---")
                st.subheader("📅 Predicted Dates")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if c.predicted_germination_date:
                        st.metric("Germination", c.predicted_germination_date, delta=f"{(c.predicted_germination_date - datetime.date.today()).days} days")
                with col2:
                    if c.predicted_transplant_date:
                        st.metric("Transplant", c.predicted_transplant_date, delta=f"{(c.predicted_transplant_date - datetime.date.today()).days} days")
                with col3:
                    if c.predicted_first_harvest_date:
                        st.metric("First Harvest", c.predicted_first_harvest_date, delta=f"{(c.predicted_first_harvest_date - datetime.date.today()).days} days")
                with col4:
                    if c.predicted_last_harvest_date:
                        st.metric("Last Harvest", c.predicted_last_harvest_date, delta=f"{(c.predicted_last_harvest_date - datetime.date.today()).days} days")
                
                st.write("---")
                st.subheader("✏️ Update Actual Dates")
                with st.form(f"actuals_{c.id}"):
                    act_germ = st.date_input(
                        "Actual Germination",
                        value=c.actual_germination_date if c.actual_germination_date else None,
                        key=f"ag_{c.id}",
                        help=(
                            "Mark this date when you see the seedling's first shoot breaking the soil surface. "
                            "For pre-germinated seeds: mark when the radicle (white root tip) first appears on the paper towel — "
                            "typically 3–7 days after placing seeds in a warm, damp environment. "
                            "Sow into compost as soon as the radicle is 1–3 mm; don't wait until it's long or it becomes fragile."
                        )
                    )
                    act_trans = st.date_input(
                        "Actual Transplant",
                        value=c.actual_transplant_date if c.actual_transplant_date else None,
                        key=f"at_{c.id}",
                        help=(
                            "Mark this date when you move seedlings to their final outdoor location. "
                            "Seedlings are ready to transplant when they have developed their first pair of TRUE leaves — "
                            "these are the second set of leaves to appear, with the characteristic shape of the crop. "
                            "The first leaves (cotyledons) are round and generic-looking; ignore those for timing. "
                            "Always harden off first: place plants outside for increasing periods over 5–7 days before final transplant. "
                            "For indoor-to-outdoor moves, wait until after last frost (mid-May in Brandenburg)."
                        )
                    )
                    act_h_start = st.date_input(
                        "Actual First Harvest",
                        value=c.actual_first_harvest_date if c.actual_first_harvest_date else None,
                        key=f"ahs_{c.id}",
                        help=(
                            "Mark this date on your first harvest from this cultivation. "
                            "Harvest indicators vary by crop: tomatoes when fully coloured and slightly soft to touch; "
                            "courgettes at 15–20 cm before they become marrows; lettuce before it bolts (sends up a flower stalk); "
                            "peas when pods are plump but before they yellow; root vegetables once shoulders are visible above soil. "
                            "For mushrooms: harvest when caps are still curled inward, before they flatten and release spores."
                        )
                    )
                    act_h_end = st.date_input(
                        "Actual Last Harvest",
                        value=c.actual_last_harvest_date if c.actual_last_harvest_date else None,
                        key=f"ahe_{c.id}",
                        help=(
                            "Mark this date when the plant is fully spent and you remove it. "
                            "Signs the harvest window is ending: leaves yellowing, fruit quality dropping, plant bolting or setting seed. "
                            "For succession crops like radishes or lettuce, clear spent plants promptly to free up space for the next sowing. "
                            "For tomatoes and courgettes, remove plants before first frost regardless of remaining fruit."
                        )
                    )
                    
                    if st.form_submit_button("Save Updates", type="primary"):
                        update_cultivation(db, c.id, {
                            "actual_germination_date": act_germ,
                            "actual_transplant_date": act_trans,
                            "actual_first_harvest_date": act_h_start,
                            "actual_last_harvest_date": act_h_end
                        })
                        st.success("✅ Updated!")
                        st.rerun()
                
                st.write("---")
                st.subheader("📊 Log Yield")
                st.markdown("<p class='help-text'>Record your harvest data after collection. Track weight and add notes about quality/performance</p>", unsafe_allow_html=True)
                with st.form(f"yield_{c.id}"):
                    yield_weight = st.number_input("Weight (kg)", min_value=0.0, step=0.1, key=f"yw_{c.id}", help="Weight of harvest in kilograms")
                    yield_date = st.date_input("Harvest Date", datetime.date.today(), key=f"yd_{c.id}")
                    yield_notes = st.text_area("Notes", key=f"yn_{c.id}", help="Quality, variety performance, or other observations")
                    
                    if st.form_submit_button("Save Yield", type="primary"):
                        create_yield(db, c.id, yield_weight, yield_date, yield_notes if yield_notes else None)
                        st.success("✅ Yield recorded!")
                        st.rerun()
                
                st.write("---")
                st.subheader("📈 Logged Yields for This Cultivation")
                yields = get_yields_by_cultivation(db, c.id)
                if yields:
                    yield_df = pd.DataFrame([{
                        "Date": y.harvest_date,
                        "Weight (kg)": y.weight_kg,
                        "Notes": y.notes or ""
                    } for y in yields])
                    st.dataframe(yield_df, use_container_width=True)
                else:
                    st.write("No yields logged yet.")
                
                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button(f"Stop/Remove Cultivation", key=f"del_c_{c.id}", use_container_width=True):
                        delete_cultivation(db, c.id)
                        st.rerun()

elif page == "Yield Tracker":
    st.header("📊 Yield Tracker")
    st.markdown("<p class='help-text'>ℹ️ Track your harvests year-over-year. Monitor yields by crop, identify top performers, and plan future seasons</p>", unsafe_allow_html=True)
    
    # Get all templates and their yields
    templates = get_templates(db)
    templates = sorted(templates, key=lambda x: (x.name.lower(), (x.variety or "").lower()))
    
    if not templates:
        st.info("No crop templates found.")
    else:
        # Create tabs for different views
        tab1, tab2, tab3 = st.tabs(["📈 Yields by Crop", "📊 Statistics", "🔍 Detailed View"])
        
        with tab1:
            st.subheader("Yields Grouped by Crop")
            
            for t in templates:
                yields = get_yields_by_crop(db, t.id)
                if yields:
                    variety_str = f" ({t.variety})" if t.variety else ""
                    with st.expander(f"🌾 {t.name}{variety_str}"):
                        # Group yields by year
                        yield_data = []
                        for y in yields:
                            year = y.harvest_date.year
                            yield_data.append({
                                "Year": year,
                                "Harvest Date": y.harvest_date,
                                "Weight (kg)": y.weight_kg,
                                "Notes": y.notes or ""
                            })
                        
                        if yield_data:
                            yield_df = pd.DataFrame(yield_data)
                            yield_df = yield_df.sort_values(["Year", "Harvest Date"], ascending=[False, True])
                            
                            st.dataframe(yield_df, use_container_width=True)
                            
                            # Summary by year
                            st.write("**Summary by Year:**")
                            yearly_summary = yield_df.groupby("Year")["Weight (kg)"].agg(["sum", "count", "mean"]).round(2)
                            yearly_summary.columns = ["Total (kg)", "Harvests", "Avg per Harvest (kg)"]
                            st.dataframe(yearly_summary, use_container_width=True)
                            
                            # Chart
                            fig = px.bar(yield_df, x="Harvest Date", y="Weight (kg)", title=f"{t.name}{variety_str} - Yield Over Time",
                                        color="Year", labels={"Weight (kg)": "Weight (kg)", "Harvest Date": "Date"})
                            st.plotly_chart(fig, use_container_width=True)
        
        with tab2:
            st.subheader("Yield Statistics")
            
            # Overall statistics
            all_yields = get_yields(db)
            if all_yields:
                total_weight = sum(y.weight_kg for y in all_yields)
                avg_weight = total_weight / len(all_yields)
                max_weight = max(y.weight_kg for y in all_yields)
                
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    st.metric("Total Yield", f"{total_weight:.2f} kg")
                with col2:
                    st.metric("Number of Harvests", len(all_yields))
                with col3:
                    st.metric("Average per Harvest", f"{avg_weight:.2f} kg")
                with col4:
                    st.metric("Largest Harvest", f"{max_weight:.2f} kg")
                
                st.divider()
                st.write("**Top Performing Crops (by total yield):**")
                
                # Calculate total yield per crop
                crop_totals = {}
                for y in all_yields:
                    cult = get_cultivation_by_id(db, y.cultivation_id)
                    if cult:
                        crop_name = f"{cult.template.name}{' (' + cult.template.variety + ')' if cult.template.variety else ''}"
                        if crop_name not in crop_totals:
                            crop_totals[crop_name] = 0
                        crop_totals[crop_name] += y.weight_kg
                
                sorted_crops = sorted(crop_totals.items(), key=lambda x: x[1], reverse=True)
                crop_df = pd.DataFrame(sorted_crops, columns=["Crop", "Total Yield (kg)"])
                
                st.dataframe(crop_df, use_container_width=True)
                
                # Chart for top crops
                fig = px.bar(crop_df, x="Crop", y="Total Yield (kg)", title="Total Yield by Crop",
                            labels={"Total Yield (kg)": "Yield (kg)"})
                fig.update_layout(xaxis_tickangle=-45)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No yield data yet. Start logging yields in 'Active Cultivations' page.")
        
        with tab3:
            st.subheader("Detailed Yield View")
            
            # Filter options
            col1, col2 = st.columns(2)
            with col1:
                selected_crop = st.selectbox("Filter by Crop", ["All Crops"] + [f"{t.name}{' (' + t.variety + ')' if t.variety else ''}" for t in templates])
            
            with col2:
                selected_year = st.selectbox("Filter by Year", ["All Years"] + sorted(list(set(y.harvest_date.year for y in get_yields(db))), reverse=True) if get_yields(db) else ["All Years"])
            
            all_yields = get_yields(db)
            filtered_yields = []
            
            for y in all_yields:
                cult = get_cultivation_by_id(db, y.cultivation_id)
                if not cult:
                    continue
                    
                crop_name = f"{cult.template.name}{' (' + cult.template.variety + ')' if cult.template.variety else ''}"
                year = y.harvest_date.year
                
                crop_match = (selected_crop == "All Crops") or (crop_name == selected_crop)
                year_match = (selected_year == "All Years") or (year == int(selected_year))
                
                if crop_match and year_match:
                    filtered_yields.append({
                        "Crop": crop_name,
                        "Year": year,
                        "Harvest Date": y.harvest_date,
                        "Weight (kg)": y.weight_kg,
                        "Notes": y.notes or "",
                        "Yield ID": y.id
                    })
            
            if filtered_yields:
                yield_df = pd.DataFrame(filtered_yields)
                yield_df = yield_df.sort_values(["Year", "Harvest Date"], ascending=[False, False])
                
                # Remove ID column for display
                display_df = yield_df.drop("Yield ID", axis=1)
                st.dataframe(display_df, use_container_width=True)
                
                st.write("**Edit or Delete Yields:**")
                for idx, row in yield_df.iterrows():
                    with st.expander(f"{row['Crop']} - {row['Harvest Date']} ({row['Weight (kg)']} kg)"):
                        col1, col2 = st.columns(2)
                        with col1:
                            with st.form(f"edit_yield_{row['Yield ID']}"):
                                new_weight = st.number_input("Weight (kg)", value=row['Weight (kg)'], min_value=0.0, step=0.1, key=f"ew_{row['Yield ID']}")
                                new_date = st.date_input("Harvest Date", value=row['Harvest Date'], key=f"ed_{row['Yield ID']}")
                                new_notes = st.text_area("Notes", value=row['Notes'], key=f"en_{row['Yield ID']}")
                                
                                if st.form_submit_button("Update Yield", type="primary"):
                                    update_yield(db, row['Yield ID'], {
                                        "weight_kg": new_weight,
                                        "harvest_date": new_date,
                                        "notes": new_notes if new_notes else None
                                    })
                                    st.success("✅ Yield updated!")
                                    st.rerun()
                        
                        with col2:
                            if st.button(f"Delete Yield", key=f"del_yield_{row['Yield ID']}", use_container_width=True):
                                delete_yield(db, row['Yield ID'])
                                st.success("✅ Yield deleted!")
                                st.rerun()
            else:
                st.info("No yield data matching the selected filters.")

elif page == "Fruit and Pruning": 
    st.header("🍎 Fruit Trees & Bushes — Pruning Tracker") 
    st.markdown( 
        "<p class='help-text'>ℹ️ Track pruning tasks for your fruit trees and bushes. " 
        "Add each plant once, then log pruning events as you complete them.</p>", 
        unsafe_allow_html=True 
    ) 

    import datetime 
    current_month = datetime.date.today().month 

    # ── Add a new plant ────────────────────────────────────────── 
    with st.expander("➕ Add a Fruit Plant", expanded=False): 
        with st.form("add_fruit_plant"): 
            species = st.selectbox( 
                "Species", 
                list(FRUIT_SPECIES.keys()), 
                help="Select the fruit type. Each species has pre-loaded pruning guidance." 
            ) 
            label = st.text_input( 
                "Your label for this plant (optional)", 
                placeholder="e.g. Old apple by the shed, Front garden cherry", 
                help="Give this plant a name so you can tell it apart if you have more than one of the same species." 
            ) 
            planted_year = st.number_input( 
                "Year planted (optional)", 
                min_value=1900, max_value=datetime.date.today().year, 
                value=datetime.date.today().year, step=1 
            ) 
            plant_notes = st.text_area( 
                "General notes", 
                placeholder="e.g. Never pruned by previous owner. Approx 5m tall.", 
                help="Anything useful to remember about this specific plant." 
            ) 
            if st.form_submit_button("Add Plant", type="primary"): 
                add_fruit_plant(db, species, label or None, planted_year or None, plant_notes or None) 
                st.success(f"✅ Added {species}{' — ' + label if label else ''}!") 
                st.rerun() 

    st.divider() 

    # ── Load all plants ─────────────────────────────────────────── 
    fruit_plants = get_fruit_plants(db) 

    if not fruit_plants: 
        st.info("No fruit plants added yet. Use the form above to add your first plant.") 
    else: 
        # ── Tasks due this month (summary across all plants) ────── 
        st.subheader(f"📅 Tasks Due This Month") 
        due_this_month = [] 
        for plant in fruit_plants: 
            for task in get_due_tasks(plant.species, current_month): 
                due_this_month.append((plant, task)) 

        if due_this_month: 
            for plant, task in due_this_month: 
                species_info = FRUIT_SPECIES[plant.species] 
                label_str = f" — {plant.label}" if plant.label else "" 
                urgency_icon = get_urgency_color(task["urgency"]) 
                st.markdown( 
                    f"{urgency_icon} **{species_info['icon']} {plant.species}{label_str}**: " 
                    f"{task['name']} *({task['month_label']})*" 
                ) 
        else: 
            st.success("✅ No pruning tasks due this month for your plants.") 

        st.divider() 

        # ── Per-plant detail ────────────────────────────────────── 
        st.subheader("🌳 Your Plants") 
        for plant in fruit_plants: 
            species_info = FRUIT_SPECIES.get(plant.species, {}) 
            icon = species_info.get("icon", "🌿") 
            label_str = f" — {plant.label}" if plant.label else "" 
            year_str = f" (planted {plant.planted_year})" if plant.planted_year else "" 

            with st.expander(f"{icon} {plant.species}{label_str}{year_str}", expanded=False): 

                # Species description 
                st.markdown( 
                    f"<p class='help-text'>{species_info.get('description', '')}</p>", 
                    unsafe_allow_html=True 
                ) 
                if plant.notes: 
                    st.markdown(f"📝 *{plant.notes}*") 

                st.write("---") 

                # ── Pruning task list with log button ───────────── 
                st.subheader("📋 Pruning Tasks") 
                logs = get_pruning_logs_for_plant(db, plant.id) 
                last_done = {log.task_key: log.done_date for log in logs} 

                for task in species_info.get("tasks", []): 
                    is_due = current_month in task["months"] 
                    urgency_icon = get_urgency_color(task["urgency"]) 
                    due_badge = " 🔔 **Due now**" if is_due else "" 
                    last_str = ( 
                        f" · Last done: **{last_done[task['key']]}**" 
                        if task["key"] in last_done else " · *Never logged*" 
                    ) 

                    st.markdown( 
                        f"{urgency_icon} **{task['name']}** " 
                        f"*({task['month_label']} · {task['type']})*" 
                        f"{due_badge}{last_str}" 
                    ) 
                    # Guidance in a nested expander — unobtrusive but always accessible 
                    with st.expander(f"ℹ️ Guidance: {task['name']}", expanded=False): 
                        st.markdown(task["guidance"]) 
                        st.markdown( 
                            f"<p class='help-text'>🔧 Tools: {task['tool_tip']}</p>", 
                            unsafe_allow_html=True 
                        ) 

                    # Log completion form inline 
                    with st.form(f"log_{plant.id}_{task['key']}"): 
                        col_date, col_note, col_btn = st.columns([2, 3, 1]) 
                        with col_date: 
                            log_date = st.date_input( 
                                "Date done", 
                                datetime.date.today(), 
                                key=f"ld_{plant.id}_{task['key']}" 
                            ) 
                        with col_note: 
                            log_note = st.text_input( 
                                "Notes (optional)", 
                                placeholder="e.g. Removed 3 large crossing branches, ~20% crown", 
                                key=f"ln_{plant.id}_{task['key']}" 
                            ) 
                        with col_btn: 
                            st.markdown("<br>", unsafe_allow_html=True) 
                            if st.form_submit_button("✅ Log"): 
                                log_pruning( 
                                    db, plant.id, task["key"], 
                                    log_date, log_note or None 
                                ) 
                                st.success("Logged!") 
                                st.rerun() 

                # ── Pruning history ─────────────────────────────── 
                if logs: 
                    st.write("---") 
                    st.subheader("📜 Pruning History") 
                    for log in sorted(logs, key=lambda l: l.done_date, reverse=True): 
                        task_name = next( 
                            (t["name"] for t in species_info.get("tasks", []) 
                             if t["key"] == log.task_key), 
                            log.task_key 
                        ) 
                        note_str = f" — {log.notes}" if log.notes else "" 
                        col_hist, col_del = st.columns([5, 1]) 
                        with col_hist: 
                            st.markdown(f"**{log.done_date}** · {task_name}{note_str}") 
                        with col_del: 
                            if st.button("🗑️", key=f"del_log_{log.id}"): 
                                delete_pruning_log(db, log.id) 
                                st.rerun() 

                # ── Delete plant ────────────────────────────────── 
                st.write("---") 
                if st.button( 
                    f"🗑️ Remove {plant.species}{label_str} from tracker", 
                    key=f"del_plant_{plant.id}", 
                    use_container_width=True 
                ): 
                    delete_fruit_plant(db, plant.id) 
                    st.rerun() 
