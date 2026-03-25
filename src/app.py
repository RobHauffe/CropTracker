import streamlit as st
from database import create_db_and_tables, seed_data, SessionLocal, CropTemplate, Cultivation, get_db
from crud import (
    create_template, get_templates, update_template, delete_template,
    start_cultivation, get_cultivations, update_cultivation, delete_cultivation,
    get_template_by_id, get_cultivation_by_id, update_cultivation_plot, update_cultivation_quantity,
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

# --- Performance Caching Helpers ---
@st.cache_data(ttl=30)  # cache for 30 seconds 
def cached_get_templates(): 
    db = next(get_db()) 
    result = get_templates(db) 
    db.close() 
    return result 
 
@st.cache_data(ttl=30) 
def cached_get_cultivations(): 
    db = next(get_db()) 
    result = get_cultivations(db) 
    db.close() 
    return result 
 
@st.cache_data(ttl=30) 
def cached_get_fruit_plants(): 
    db = next(get_db()) 
    result = get_fruit_plants(db) 
    db.close() 
    return result 

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
@st.cache_resource 
def initialise_db(): 
    create_db_and_tables() 
    db = next(get_db()) 
    if not get_templates(db): 
        seed_data(db) 
    db.close() 
    # Force clear data cache after initialization/migration to avoid stale objects
    st.cache_data.clear()
 
try:
    initialise_db()
except Exception as e:
    # Don't halt the app if seeding fails, but log it
    print(f"Database initialization info: {e}")

st.sidebar.header("📍 Navigation")
st.sidebar.markdown("---")

# Use session state to handle page navigation without widget key conflicts
if 'nav_choice' not in st.session_state:
    st.session_state.nav_choice = "Dashboard"

# We use index based on session state to avoid the "cannot be modified after instantiation" error
page_list = ["Dashboard", "Timeline", "Crop Registry", "Active Cultivations", "Raised Bed Map", "Yield Tracker", "Fruit and Pruning", "Cultivation Archive"]
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
    templates = cached_get_templates()
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
        col_sow1, col_sow2 = st.columns([2, 1])
        with col_sow1:
            sow_date = st.date_input("Sowing Date", datetime.date.today(), help="Date when you will sow the seeds")
        with col_sow2:
            sow_quantity = st.number_input("Quantity", min_value=1, value=1, help="Number of seeds sown / plants started")
        
        sow_notes = st.text_area("Initial Cultivation Notes (optional)", placeholder="e.g. Sown 12 seeds in a 3x4 tray, using organic compost.", help="Add any details about this specific sowing (quantity, location, etc.)")
        
        if st.button("Start Cultivation", type="primary"):
            if templates and selected_option in template_options:
                template_id = template_options[selected_option]
                start_cultivation(db, template_id, sow_date, sow_notes, sow_quantity)
                st.cache_data.clear()
                st.success(f"✅ Started cultivation for {selected_option}!")
                st.rerun()
            else:
                st.error("Please select a valid crop or add one to the Registry.")

    # Dashboard Status
    st.divider()
    cultivations = cached_get_cultivations()
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
        
        # New: Quick Quantity Adjust section
        st.divider()
        st.subheader("🔢 Quick Adjust Plant Quantity")
        st.markdown("<p class='help-text'>ℹ️ Update the number of actual living plants if some didn't germinate or were lost.</p>", unsafe_allow_html=True)
        
        # Filter for active ones and sort by name
        active_c = [c for c in cultivations if getattr(c, 'is_archived', 0) == 0]
        
        if active_c:
            # Let's use a selectbox to pick which one to adjust to keep the dashboard clean
            adjust_options = {f"{c.template.name}{' (' + c.template.variety + ')' if c.template.variety else ''} (Sown: {c.sow_date})": c for c in active_c}
            selected_to_adjust = st.selectbox("Select cultivation to adjust quantity", options=list(adjust_options.keys()), key="adjust_qty_sel")
            
            if selected_to_adjust:
                target_c = adjust_options[selected_to_adjust]
                col_q1, col_q2 = st.columns([1, 2])
                with col_q1:
                    new_qty = st.number_input("New Quantity", min_value=1, value=getattr(target_c, 'quantity', 1), key=f"new_qty_{target_c.id}")
                with col_q2:
                    st.write("") # padding
                    st.write("") # padding
                    if st.button("Update Quantity", key=f"btn_qty_{target_c.id}", type="secondary"):
                        update_cultivation_quantity(db, target_c.id, new_qty)
                        st.cache_data.clear()
                        st.success(f"✅ Updated {target_c.template.name} to {new_qty} plants!")
                        st.rerun()
        else:
            st.write("No active cultivations to adjust.")

elif page == "Timeline":
    st.header("📈 Active Cultivations Timeline")
    st.markdown("<p class='help-text'>ℹ️ Visualize all your cultivations on a timeline showing germination, transplant, and harvest phases</p>", unsafe_allow_html=True)
    
    cultivations = cached_get_cultivations()
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
                # The growth phase (indoor/pot) starts after germination and ends at transplant
                start_date = c.predicted_germination_date if c.predicted_germination_date else c.sow_date
                # Only add if there's actually a duration to show
                if c.predicted_transplant_date > start_date:
                    timeline_data.append(dict(Task=label, Start=start_date, Finish=c.predicted_transplant_date, Resource="Growth (to Transplant)"))
            
            if c.predicted_first_harvest_date:
                finish = c.predicted_last_harvest_date if c.predicted_last_harvest_date else c.predicted_first_harvest_date + datetime.timedelta(days=14)
                timeline_data.append(dict(Task=label, Start=c.predicted_first_harvest_date, Finish=finish, Resource="Harvest"))

        if timeline_data:
            df = pd.DataFrame(timeline_data)
            fig = px.timeline(df, x_start="Start", x_end="Finish", y="Task", color="Resource",
                            color_discrete_map={
                                "Germination": "#3498db", 
                                "Growth (to Transplant)": "#f39c12", 
                                "Harvest": "#27ae60"
                            })
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(height=500)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.write("Not enough data for timeline.")

elif page == "Crop Registry":
    st.header("🌿 Crop Registry (Templates)")
    st.markdown("<p class='help-text'>ℹ️ Manage your crop templates. Add new crop types and varieties with expected growth timelines</p>", unsafe_allow_html=True)
    
    with st.expander("➕ Add New Template", expanded=False):
        templates = cached_get_templates()
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
                    st.cache_data.clear()
                    st.success(f"✅ Added {final_name} {variety if variety else ''} to Registry!")
                    st.rerun()

    st.divider()
    st.subheader("📚 Registry Templates")
    templates = cached_get_templates()
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
                
                col_actions = st.columns(2)
                with col_actions[0]:
                    with st.popover(f"✏️ Edit {t.name}", use_container_width=True):
                        with st.form(f"edit_t_{t.id}"):
                            edit_name = st.text_input("Crop Name", value=t.name)
                            edit_variety = st.text_input("Variety", value=t.variety or "")
                            edit_loc = st.selectbox("Sow Location", ["Indoor", "Direct outside", "Grow bag"], 
                                                   index=["Indoor", "Direct outside", "Grow bag"].index(t.sow_location) if t.sow_location in ["Indoor", "Direct outside", "Grow bag"] else 0)
                            edit_germ = st.number_input("Days to Germination", value=t.expected_days_to_germination or 0, min_value=0)
                            edit_trans = st.number_input("Days to Transplant", value=t.expected_days_to_transplant or 0, min_value=0)
                            edit_h_start = st.number_input("Days to First Harvest", value=t.expected_days_to_first_harvest or 0, min_value=0)
                            edit_h_end = st.number_input("Days to Last Harvest", value=t.expected_days_to_last_harvest or 0, min_value=0)
                            edit_notes = st.text_area("Notes", value=t.notes or "")
                            
                            if st.form_submit_button("Update Template", type="primary"):
                                update_template(db, t.id, {
                                    "name": edit_name, "variety": edit_variety or None, 
                                    "sow_location": edit_loc,
                                    "expected_days_to_germination": edit_germ,
                                    "expected_days_to_transplant": edit_trans,
                                    "expected_days_to_first_harvest": edit_h_start,
                                    "expected_days_to_last_harvest": edit_h_end,
                                    "notes": edit_notes or None
                                })
                                st.cache_data.clear()
                                st.success("✅ Updated!")
                                st.rerun()
                
                with col_actions[1]:
                    if st.button(f"Delete {t.name}{variety_str}", key=f"del_t_{t.id}", use_container_width=True):
                        delete_template(db, t.id)
                        st.cache_data.clear()
                        st.rerun()

elif page == "Active Cultivations":
    st.header("🌾 Active Cultivations")
    st.markdown("<p class='help-text'>ℹ️ Track the progress of your current cultivations. Update actual dates and log yields when ready</p>", unsafe_allow_html=True)
    
    cultivations = cached_get_cultivations()
    # Filter only active ones
    active_cultivations = [c for c in cultivations if getattr(c, 'is_archived', 0) == 0]
    # Sort cultivations alphabetically
    active_cultivations = sorted(active_cultivations, key=lambda x: (x.template.name.lower(), (x.template.variety or "").lower()))
    
    if not active_cultivations:
        st.info("No crops in cultivation.")
    else:
        for c in active_cultivations:
            variety_str = f" ({c.template.variety})" if c.template.variety else ""
            progress = get_cultivation_progress(c)
            stage = get_cultivation_stage(c)
            
            with st.expander(f"{c.template.name}{variety_str} ({getattr(c, 'quantity', 1)} plants) - Sown: {c.sow_date} | {stage}", expanded=False):
                # Progress bar
                st.progress(progress / 100, text=f"Progress: {progress:.0f}%")
                
                # Cultivation Notes
                st.write("---")
                st.subheader("📝 Cultivation Notes")
                with st.form(f"notes_{c.id}"):
                    current_notes = getattr(c, 'notes', "") or ""
                    new_notes = st.text_area("Ongoing Notes", value=current_notes, key=f"notes_input_{c.id}", help="Update notes for this cultivation (quantity, location, performance, etc.)")
                    if st.form_submit_button("Update Notes"):
                        update_cultivation(db, c.id, {"notes": new_notes})
                        st.cache_data.clear()
                        st.success("✅ Notes updated!")
                        st.rerun()

                st.write("---")
                st.subheader("📅 Predicted Dates")
                col1, col2, col3, col4 = st.columns(4)
                with col1:
                    if c.predicted_germination_date:
                        st.metric("Germination", str(c.predicted_germination_date), delta=f"{(c.predicted_germination_date - datetime.date.today()).days} days")
                with col2:
                    if c.predicted_transplant_date:
                        st.metric("Transplant", str(c.predicted_transplant_date), delta=f"{(c.predicted_transplant_date - datetime.date.today()).days} days")
                with col3:
                    if c.predicted_first_harvest_date:
                        st.metric("First Harvest", str(c.predicted_first_harvest_date), delta=f"{(c.predicted_first_harvest_date - datetime.date.today()).days} days")
                with col4:
                    if c.predicted_last_harvest_date:
                        st.metric("Last Harvest", str(c.predicted_last_harvest_date), delta=f"{(c.predicted_last_harvest_date - datetime.date.today()).days} days")
                
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
                        st.cache_data.clear()
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
                        st.cache_data.clear()
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
                    if st.button(f"Archive Cultivation", key=f"arc_c_{c.id}", use_container_width=True, help="Move this cultivation to the Archive (e.g. after full harvest or failure)"):
                        update_cultivation(db, c.id, {"is_archived": 1})
                        st.cache_data.clear()
                        st.success(f"✅ {c.template.name} moved to Archive!")
                        st.rerun()
                with col_btn2:
                    if st.button(f"Delete Cultivation", key=f"del_c_{c.id}", use_container_width=True, help="Permanently delete this cultivation and its yields"):
                        delete_cultivation(db, c.id)
                        st.cache_data.clear()
                        st.rerun()

elif page == "Yield Tracker":
    st.header("📊 Yield Tracker")
    st.markdown("<p class='help-text'>ℹ️ Track your harvests year-over-year. Monitor yields by crop, identify top performers, and plan future seasons</p>", unsafe_allow_html=True)
    
    # Get all templates and their yields
    templates = cached_get_templates()
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
                            # Add quantity to yield_df if we can find it
                            # (Note: this is a bit tricky as yields are linked to cultivations)
                            # For now, let's just use the totals
                            
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
                
                # Calculate total yield per crop and yield per plant
                crop_stats = {}
                for y in all_yields:
                    cult = get_cultivation_by_id(db, y.cultivation_id)
                    if cult:
                        crop_name = f"{cult.template.name}{' (' + cult.template.variety + ')' if cult.template.variety else ''}"
                        if crop_name not in crop_stats:
                            crop_stats[crop_name] = {"total_yield": 0, "quantity": getattr(cult, 'quantity', 1)}
                        crop_stats[crop_name]["total_yield"] += y.weight_kg
                
                # Convert to DataFrame
                stats_list = []
                for crop, data in crop_stats.items():
                    stats_list.append({
                        "Crop": crop,
                        "Total Yield (kg)": round(data["total_yield"], 2),
                        "Plants": data["quantity"],
                        "Yield per Plant (kg)": round(data["total_yield"] / data["quantity"], 2) if data["quantity"] > 0 else 0
                    })
                
                crop_df = pd.DataFrame(stats_list)
                crop_df = crop_df.sort_values("Total Yield (kg)", ascending=False)
                
                st.dataframe(crop_df, use_container_width=True)
                
                # Chart for top crops
                fig = px.bar(crop_df, x="Crop", y="Total Yield (kg)", title="Total Yield by Crop",
                            hover_data=["Yield per Plant (kg)", "Plants"],
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
                                    st.cache_data.clear()
                                    st.success("✅ Yield updated!")
                                    st.rerun()
                        
                        with col2:
                            if st.button(f"Delete Yield", key=f"del_yield_{row['Yield ID']}", use_container_width=True):
                                delete_yield(db, row['Yield ID'])
                                st.cache_data.clear()
                                st.success("✅ Yield deleted!")
                                st.rerun()
            else:
                st.info("No yield data matching the selected filters.")

elif page == "Raised Bed Map":
    st.header("🗺️ Raised Bed Map")
    st.markdown("<p class='help-text'>ℹ️ Visual top-down map of your raised bed layout and plot assignments</p>", unsafe_allow_html=True)

    # ── SVG Configuration ──────────────────────────────────────────
    # Scale: 1 cm = 2.5 px
    # Main bar cell (halved width): 35cm x 30cm -> 87.5px x 75px
    # Protrusion cell: 45cm x 30cm -> 112.5px x 75px
    
    cell_w_main = 87.5
    cell_w_prot = 112.5
    cell_h = 75
    gap = 12
    
    # Coordinates for all 34 cells (16x2 + 2)
    # Row: Back (0), Front (1)
    # Col: 1-16 (Main Bar)
    cells = {}
    
    # Main Bar (16x2)
    for r_idx, row_label in enumerate(["Back", "Front"]):
        y = r_idx * (cell_h + gap)
        for c_idx in range(1, 17):
            x = (c_idx - 1) * cell_w_main
            cells[f"{row_label}-{c_idx}"] = {"x": x, "y": y, "w": cell_w_main, "h": cell_h}
            
    # Protrusion (1x2) - Right-1 (top) and Right-2 (front)
    # Aligned to the right edges of column 16, extending downward
    x_prot_align_right = (16 * cell_w_main) - cell_w_prot
    y_prot_1 = 2 * (cell_h + gap)
    y_prot_2 = 3 * (cell_h + gap)
    
    cells["Right-1"] = {"x": x_prot_align_right, "y": y_prot_1, "w": cell_w_prot, "h": cell_h}
    cells["Right-2"] = {"x": x_prot_align_right, "y": y_prot_2, "w": cell_w_prot, "h": cell_h}

    # Total SVG Dimensions
    svg_width = (16 * cell_w_main) + 20
    svg_height = y_prot_2 + cell_h + 20
    
    all_addresses = list(cells.keys())

    # ── Load Cultivations and Map to Cells ──────────────────────────
    cultivations = cached_get_cultivations()
    active_cultivations = [c for c in cultivations if getattr(c, 'is_archived', 0) == 0]
    
    # Map cell address to cultivation
    cell_assignments = {}
    for c in active_cultivations:
        if c.plot_address:
            addresses = c.plot_address.split(',')
            for addr in addresses:
                addr = addr.strip()
                if addr in cells:
                    cell_assignments[addr] = c

    # ── Rendering Logic ─────────────────────────────────────────────
    def get_cell_color(c):
        if not c: return "#f5f5f0" # Empty
        
        today = datetime.date.today()
        # Stage logic matching timeline
        if c.actual_last_harvest_date and today > c.actual_last_harvest_date:
            return "#e74c3c" # Overdue/Finished
        elif c.predicted_last_harvest_date and today > c.predicted_last_harvest_date and not c.actual_last_harvest_date:
            return "#e74c3c" # Overdue
        elif (c.actual_first_harvest_date and today >= c.actual_first_harvest_date) or \
             (c.predicted_first_harvest_date and today >= c.predicted_first_harvest_date):
            return "#27ae60" # Harvest
        elif (c.actual_transplant_date and today >= c.actual_transplant_date) or \
             (c.predicted_transplant_date and today >= c.predicted_transplant_date):
            return "#f39c12" # Transplant/Growth
        elif today >= c.sow_date:
            return "#3498db" # Germination
        else:
            return "#bdc3c7" # Upcoming

    def get_text_color(bg_color):
        # Simple contrast check
        if bg_color in ["#3498db", "#27ae60", "#e74c3c"]:
            return "white"
        return "#2d5020"

    svg_content = f'<svg width="{svg_width}" height="{svg_height}" viewBox="0 0 {svg_width} {svg_height}" xmlns="http://www.w3.org/2000/svg">'
    
    # Draw outer boundary
    # (Approximation of the L-shape)
    path_d = f"M 0,0 H {16*cell_w_main} V {y_prot_2+cell_h} H {x_prot_align_right} V {2*cell_h+gap} H 0 Z"
    svg_content += f'<path d="{path_d}" fill="none" stroke="#2d5020" stroke-width="3" />'

    # ── Rendering Pass 1: Background Rectangles ──────────────────────
    for addr, dims in cells.items():
        c = cell_assignments.get(addr)
        bg_color = get_cell_color(c)
        svg_content += f'<rect x="{dims["x"]}" y="{dims["y"]}" width="{dims["w"]}" height="{dims["h"]}" fill="{bg_color}" stroke="#2d5020" stroke-width="1.5" />'

    # ── Rendering Pass 2: Address Labels (Small) ──────────────────────
    for addr, dims in cells.items():
        svg_content += f'<text x="{dims["x"]+5}" y="{dims["y"]+15}" font-family="sans-serif" font-size="11" fill="#7f8c8d">{addr}</text>'

    # ── Rendering Pass 3: Crop Names & Milestones ─────────────────────
    rendered_centered_cultivations = set()

    for addr, dims in cells.items():
        c = cell_assignments.get(addr)
        if not c:
            continue
            
        bg_color = get_cell_color(c)
        text_color = get_text_color(bg_color)
        qty = getattr(c, 'quantity', 1)
        
        # Determine if we should render a centered label or individual label
        # Case 1: Multiple plants -> Render in every assigned cell
        if qty > 1:
            display_w = dims["w"]
            display_x = dims["x"]
            render_here = True
        # Case 2: Single plant -> Render once, centered across all assigned cells
        else:
            if c.id in rendered_centered_cultivations:
                continue
            
            display_w = dims["w"]
            display_x = dims["x"]
            render_here = True
            
            if "," in (c.plot_address or ""):
                addresses = [a.strip() for a in c.plot_address.split(',')]
                # Only start rendering from the first address in the list
                if addr == addresses[0]:
                    # Find all assigned cells that are on the same row and consecutive
                    # (For simplicity, we check horizontal continuity)
                    consecutive_addrs = []
                    for a in addresses:
                        if a in cells and cells[a]["y"] == dims["y"]:
                            consecutive_addrs.append(a)
                        else:
                            break # Stop at first break or row change
                    
                    if len(consecutive_addrs) > 1:
                        rightmost_addr = consecutive_addrs[-1]
                        display_w = (cells[rightmost_addr]["x"] + cells[rightmost_addr]["w"]) - display_x
                    
                    rendered_centered_cultivations.add(c.id)
                else:
                    render_here = False

        if render_here:
            # Crop Name
            crop_name = f"{c.template.name}"
            # Font size and truncation based on width
            font_size = 14 if display_w > 100 else 11
            max_chars = 25 if display_w > 100 else 12
            
            if len(crop_name) > max_chars:
                crop_name = crop_name[:max_chars-3] + "..."
            
            svg_content += f'<text x="{display_x + display_w/2}" y="{dims["y"]+42}" font-family="sans-serif" font-weight="bold" font-size="{font_size}" fill="{text_color}" text-anchor="middle">{crop_name}</text>'
            
            # Next Milestone
            milestone_text = ""
            today = datetime.date.today()
            if not c.actual_germination_date and c.predicted_germination_date:
                milestone_text = f"G:{c.predicted_germination_date.strftime('%d%b')}"
            elif not c.actual_transplant_date and c.predicted_transplant_date:
                milestone_text = f"T:{c.predicted_transplant_date.strftime('%d%b')}"
            elif not c.actual_first_harvest_date and c.predicted_first_harvest_date:
                milestone_text = f"H:{c.predicted_first_harvest_date.strftime('%d%b')}"
            
            if milestone_text and display_w > 60:
                svg_content += f'<text x="{display_x + display_w/2}" y="{dims["y"]+62}" font-family="sans-serif" font-size="10" fill="{text_color}" text-anchor="middle">{milestone_text}</text>'

    svg_content += '</svg>'
    
    # Display SVG
    st.markdown(f'<div style="overflow-x: auto; padding: 10px; background-color: white; border-radius: 8px;">{svg_content}</div>', unsafe_allow_html=True)

    # ── Legend ─────────────────────────────────────────────────────
    st.write("")
    legend_cols = st.columns(6)
    legend_items = [
        ("#f5f5f0", "Empty"),
        ("#3498db", "Germination"),
        ("#f39c12", "Transplant/Growth"),
        ("#27ae60", "Harvest"),
        ("#e74c3c", "Overdue/End"),
        ("#bdc3c7", "Upcoming")
    ]
    for i, (color, label) in enumerate(legend_items):
        with legend_cols[i]:
            st.markdown(f'<div style="display: flex; align-items: center;"><div style="width: 15px; height: 15px; background-color: {color}; border: 1px solid #999; margin-right: 5px;"></div><span style="font-size: 12px;">{label}</span></div>', unsafe_allow_html=True)

    # ── Plot Assignment UI ─────────────────────────────────────────
    st.divider()
    with st.expander("📌 Assign Cultivations to Plots", expanded=True):
        # Sort: Unassigned first, then by name
        sorted_cults = sorted(active_cultivations, key=lambda x: (0 if not x.plot_address else 1, x.template.name.lower()))
        
        for c in sorted_cults:
            variety_str = f" ({c.template.variety})" if c.template.variety else ""
            current_addrs = [a.strip() for a in (c.plot_address or "").split(",") if a.strip() in all_addresses]
            
            with st.form(f"assign_{c.id}"):
                st.write(f"**{c.template.name}{variety_str}** — {getattr(c, 'quantity', 1)} plants (Sown: {c.sow_date})")
                
                col_sel, col_btn = st.columns([4, 1])
                
                with col_sel:
                    new_selection = st.multiselect(
                        f"Select plots for {c.template.name} (Max {getattr(c, 'quantity', 1)})",
                        options=all_addresses,
                        default=current_addrs,
                        key=f"ms_{c.id}",
                        max_selections=getattr(c, 'quantity', 1) if getattr(c, 'quantity', 1) > 0 else None,
                        help=f"Select up to {getattr(c, 'quantity', 1)} plots for these plants."
                    )
                
                with col_btn:
                    st.write("") # Spacer
                    st.write("") # Spacer
                    if st.form_submit_button("Save", type="primary", use_container_width=True):
                        final_address = ",".join(new_selection) if new_selection else None
                        update_cultivation_plot(db, c.id, final_address)
                        st.cache_data.clear()
                        st.success("Saved!")
                        st.rerun()

    # ── Rotation Planning Reference ───────────────────────────────
    with st.expander("🔄 Crop Rotation Reference", expanded=False):
        rotation_data = [
            {"Family": "Solanaceae", "Crops in this app": "Tomatoes, Peppers, Chillies, Aubergine, Potatoes", "Min Gap": "3-4 years", "Follows well": "Legumes, Alliums", "Avoid following": "Other Solanaceae", "Notes": "Heavy feeders; potato blight risk; same pests"},
            {"Family": "Brassica", "Crops in this app": "Kale, Kohlrabi, Pak choi, Asian greens", "Min Gap": "4 years", "Follows well": "Legumes (Nitrogen!)", "Avoid following": "Other Brassicas", "Notes": "Clubroot risk; needs firm soil; high Nitrogen needs"},
            {"Family": "Legume", "Crops in this app": "Peas, Broad beans, French beans", "Min Gap": "2-3 years", "Follows well": "Roots, Brassicas", "Avoid following": "Legumes", "Notes": "Fixes nitrogen in soil; great before Brassicas"},
            {"Family": "Root", "Crops in this app": "Carrots, Parsnips, Beetroot", "Min Gap": "3 years", "Follows well": "Any (except Roots)", "Avoid following": "Manured soil", "Notes": "Fresh manure causes forking; light soil best"},
            {"Family": "Cucurbit", "Crops in this app": "Courgette, Cucumber, Pumpkin, Squash", "Min Gap": "2 years", "Follows well": "Legumes", "Avoid following": "Cucurbits", "Notes": "Very heavy feeders; need lots of organic matter"},
            {"Family": "Allium", "Crops in this app": "Leeks", "Min Gap": "3-4 years", "Follows well": "Any", "Avoid following": "Alliums", "Notes": "Onion fly/rot risk; good break crop"},
            {"Family": "Leafy", "Crops in this app": "Lettuce, Spinach, Lamb's lettuce, Chard", "Min Gap": "1-2 years", "Follows well": "Any", "Avoid following": "Leafy", "Notes": "Quick crops; can often fit between others"}
        ]
        st.table(rotation_data)
        
        st.markdown("""
        ### 💡 Practical Rotation Advice
        - **Protrusion (Right-1, Right-2):** Best reserved for **Solanaceae** (chillies, peppers) as it typically gets the most sun exposure.
        - **The Golden Rule:** **Legumes** should ideally precede **Brassicas** because legumes leave nitrogen in the soil which brassicas crave.
        - **Space Savers:** Leafy greens (lettuce, spinach) are fast and flexible; use them to fill gaps between longer-term crops.
        - **Diversity:** Even if you can't follow a perfect 4-year cycle, just ensuring you don't plant the same family in the same spot twice in a row helps significantly.
        """)
        
        st.subheader("⚠️ Rotation Conflict Checker")
        check_c = st.selectbox("Select a cultivation to check", active_cultivations, 
                              format_func=lambda x: f"{x.template.name}{' ('+x.template.variety+')' if x.template.variety else ''} (Plot: {x.plot_address or 'N/A'})")
        
        if check_c and check_c.plot_address:
            # Map crop to family (simple mapping for this app)
            family_map = {
                "Tomato": "Solanaceae", "Peppers": "Solanaceae", "Aubergine": "Solanaceae", "Potatoes": "Solanaceae",
                "Kale": "Brassica", "Kohlrabi": "Brassica", "Pak choi": "Brassica", "Asian greens": "Brassica",
                "Peas": "Legume", "Broad beans": "Legume", "French beans": "Legume",
                "Carrots": "Root", "Parsnips": "Root", "Beetroot": "Root",
                "Courgette": "Cucurbit", "Cucumber": "Cucurbit", "Pumpkin": "Cucurbit", "Squash": "Cucurbit",
                "Leeks": "Allium",
                "Lettuce": "Leafy", "Spinach": "Leafy", "Lamb's lettuce": "Leafy", "Chard": "Leafy"
            }
            
            def get_family(name):
                for key, fam in family_map.items():
                    if key in name: return fam
                return "Unknown"
            
            curr_fam = get_family(check_c.template.name)
            curr_plots = [p.strip() for p in (check_c.plot_address or "").split(",") if p.strip()]
            
            # Find history for these plots in previous years
            # We fetch all previous cultivations and check for plot overlap in Python
            all_prev_cults = db.query(Cultivation).filter(
                Cultivation.sow_date < datetime.date(check_c.sow_date.year, 1, 1)
            ).all()
            
            plot_history = []
            for prev in all_prev_cults:
                if not prev.plot_address:
                    continue
                prev_plots = [p.strip() for p in prev.plot_address.split(",") if p.strip()]
                if any(p in curr_plots for p in prev_plots):
                    plot_history.append(prev)
            
            if plot_history:
                last_year = max(c.sow_date.year for c in plot_history)
                last_year_cults = [c for c in plot_history if c.sow_date.year == last_year]
                
                conflicts = []
                for prev in last_year_cults:
                    prev_fam = get_family(prev.template.name)
                    if prev_fam == curr_fam and curr_fam != "Unknown":
                        conflicts.append(f"{prev.template.name} ({prev_fam})")
                
                if conflicts:
                    st.warning(f"🚨 **Potential Rotation Conflict!** This plot was used for **{', '.join(conflicts)}** in {last_year}. Both are in the **{curr_fam}** family.")
                else:
                    st.success(f"✅ **Rotation looks good!** Previous crops in {last_year} were from different families.")
            else:
                st.info("ℹ️ No prior season data available for this plot to check rotation.")

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
                st.cache_data.clear()
                st.success(f"✅ Added {species}{' — ' + label if label else ''}!") 
                st.rerun() 

    st.divider() 

    # ── Load all plants ─────────────────────────────────────────── 
    fruit_plants = cached_get_fruit_plants() 

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
                                st.cache_data.clear()
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
                                st.cache_data.clear()
                                st.rerun() 

                # ── Delete plant ────────────────────────────────── 
                st.write("---") 
                if st.button( 
                    f"🗑️ Remove {plant.species}{label_str} from tracker", 
                    key=f"del_plant_{plant.id}", 
                    use_container_width=True 
                ): 
                    delete_fruit_plant(db, plant.id) 
                    st.cache_data.clear()
                    st.rerun() 

        # ── Pruning Timeline (Gantt Chart) ────────────────────────
        st.divider()
        st.subheader("📅 Pruning Timeline — Full Year")
        st.markdown(
            "<p class='help-text'>ℹ️ Visualize pruning windows for all your plants. "
            "The vertical line indicates today's date.</p>",
            unsafe_allow_html=True
        )

        timeline_data = []
        current_year = datetime.date.today().year
        
        for plant in fruit_plants:
            species_info = FRUIT_SPECIES.get(plant.species, {})
            label_str = f" — {plant.label}" if plant.label else ""
            display_name = f"{plant.species}{label_str}"
            
            for task in species_info.get("tasks", []):
                # We need to handle month ranges that might wrap around or be disconnected
                # For simplicity in a yearly Gantt, we'll create a segment for each continuous month block
                months = sorted(task["months"])
                if not months:
                    continue
                
                # Group continuous months into segments
                segments = []
                if months:
                    start_m = months[0]
                    prev_m = months[0]
                    for m in months[1:]:
                        if m != prev_m + 1:
                            segments.append((start_m, prev_m))
                            start_m = m
                        prev_m = m
                    segments.append((start_m, prev_m))
                
                for start_m, end_m in segments:
                    # Create start and end dates for the segment in the current year
                    # Start of the start month
                    start_date = datetime.date(current_year, start_m, 1)
                    # End of the end month (first day of next month - 1 day)
                    if end_m == 12:
                        end_date = datetime.date(current_year, 12, 31)
                    else:
                        end_date = datetime.date(current_year, end_m + 1, 1) - datetime.timedelta(days=1)
                    
                    timeline_data.append(dict(
                        Task=display_name,
                        Start=start_date,
                        Finish=end_date,
                        Resource=task["name"],
                        Species=plant.species
                    ))

        if timeline_data:
            df = pd.DataFrame(timeline_data)
            # Create the Gantt chart
            fig = px.timeline(
                df, 
                x_start="Start", 
                x_end="Finish", 
                y="Task", 
                color="Resource",
                hover_data=["Resource", "Species"],
                title="Yearly Pruning Windows",
                color_discrete_map={
                    "Winter Renovation Prune": "#3498db",  # Blue for winter
                    "Winter Prune": "#3498db",
                    "Summer Tidy — Water Shoots": "#f1c40f", # Yellow for summer
                    "Fruit Thinning": "#2ecc71",             # Green for fruit tasks
                    "Summer Prune (Post-Harvest)": "#e67e22",# Orange for post-harvest
                    "Post-Harvest Prune": "#e67e22",
                    "Post-Harvest Prune (Summer Varieties)": "#e67e22",
                    "Post-Harvest Prune (Autumn Varieties)": "#d35400",
                    "Disease & Silver Leaf Check": "#e74c3c",# Red for disease checks
                    "Identify Variety Type": "#95a5a6",      # Grey for one-off
                    "Summer Shoot Pinch": "#27ae60",
                    "New Cane Tip Pruning": "#16a085"
                }
            )
            
            # Add vertical "Today" line
            today = datetime.date.today()
            fig.add_vline(x=today.strftime("%Y-%m-%d"), line_width=3, line_dash="dash", line_color="red")
            fig.add_annotation(
                x=today.strftime("%Y-%m-%d"), 
                y=1.05, 
                yref="paper",
                text="Today", 
                showarrow=False, 
                font=dict(color="red", size=12)
            )

            # Set x-axis range to the full year
            fig.update_xaxes(
                range=[f"{current_year}-01-01", f"{current_year}-12-31"],
                dtick="M1",  # Tick every month
                tickformat="%b" # Month name abbreviation
            )
            
            fig.update_yaxes(autorange="reversed")
            fig.update_layout(
                height=400 + (len(fruit_plants) * 30), # Scale height with number of plants
                showlegend=True,
                margin=dict(l=20, r=20, t=60, b=20)
            )
            
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No plants or tasks found to display on the timeline.")

elif page == "Cultivation Archive":
    st.header("📂 Cultivation Archive")
    st.markdown("<p class='help-text'>ℹ️ Revisit your completed cultivations. Review what worked, check your notes, and compare yields across years.</p>", unsafe_allow_html=True)
    
    cultivations = cached_get_cultivations()
    archived = [c for c in cultivations if getattr(c, 'is_archived', 0) == 1]
    
    if not archived:
        st.info("Your archive is empty. You can move cultivations here from the 'Active Cultivations' tab once they are finished.")
    else:
        # Search and filter
        search_term = st.text_input("Search Archive (Crop or Variety)", "").lower()
        filtered_archived = [c for c in archived if search_term in c.template.name.lower() or (c.template.variety and search_term in c.template.variety.lower())]
        
        # Sort by sow date descending (newest first)
        filtered_archived = sorted(filtered_archived, key=lambda x: x.sow_date, reverse=True)
        
        # Before the loop — fetch all yields once 
        all_yield_records = get_yields(db) 
        yields_by_cultivation = {} 
        for y in all_yield_records: 
            yields_by_cultivation.setdefault(y.cultivation_id, []).append(y) 

        for c in filtered_archived:
            variety_str = f" ({c.template.variety})" if c.template.variety else ""
            year = c.sow_date.year
            with st.expander(f"📦 {c.template.name}{variety_str} ({getattr(c, 'quantity', 1)} plants) — {year} (Sown: {c.sow_date})"):
                col1, col2 = st.columns(2)
                with col1:
                    st.write("**📅 Key Dates**")
                    st.write(f"- Sown: {c.sow_date}")
                    if c.actual_germination_date: st.write(f"- Germinated: {c.actual_germination_date}")
                    if c.actual_transplant_date: st.write(f"- Transplanted: {c.actual_transplant_date}")
                    if c.actual_first_harvest_date: st.write(f"- First Harvest: {c.actual_first_harvest_date}")
                    if c.actual_last_harvest_date: st.write(f"- Last Harvest: {c.actual_last_harvest_date}")
                
                with col2:
                    st.write("**📊 Harvest Summary**")
                    yields = yields_by_cultivation.get(c.id, [])
                    if yields:
                        total_weight = sum(y.weight_kg for y in yields)
                        st.metric("Total Yield", f"{total_weight:.2f} kg")
                        st.write(f"Logged over {len(yields)} harvests")
                    else:
                        st.write("No yields recorded.")
                
                st.write("---")
                st.write("**📝 Cultivation Notes**")
                if c.notes:
                    st.info(c.notes)
                else:
                    st.write("*No notes recorded for this cultivation.*")
                
                # History of individual yields
                if yields:
                    with st.expander("🔍 View Individual Yield Logs"):
                        yield_df = pd.DataFrame([{
                            "Date": y.harvest_date,
                            "Weight (kg)": y.weight_kg,
                            "Notes": y.notes or ""
                        } for y in yields])
                        st.dataframe(yield_df, use_container_width=True)

                col_btn1, col_btn2 = st.columns(2)
                with col_btn1:
                    if st.button(f"Unarchive", key=f"unarc_{c.id}", use_container_width=True, help="Move back to Active Cultivations"):
                        update_cultivation(db, c.id, {"is_archived": 0})
                        st.cache_data.clear()
                        st.rerun()
                with col_btn2:
                    if st.button(f"Delete Permanently", key=f"del_arch_{c.id}", use_container_width=True):
                        delete_cultivation(db, c.id)
                        st.cache_data.clear()
                        st.rerun()
