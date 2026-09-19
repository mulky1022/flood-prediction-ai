/**
 * Centralized Internationalization (i18n) Engine for Sri Lanka FloodWatch
 * Supports English (en), Sinhala (si), and Tamil (ta).
 * 
 * CORE INVARIANT: LANGUAGE CHANGES PRESENTATION, NOT DATA.
 */

const STORAGE_KEY = 'floodwatch_lang';
const DEFAULT_LANG = 'en';
const SUPPORTED_LANGS = ['en', 'si', 'ta'];

const translations = {
  en: {
    // Navigation & General UI
    'nav.home': 'Live Dashboard',
    'nav.map': 'Flood Map',
    'nav.details': 'Location Details',
    'nav.alerts': 'Alerts & History',
    'nav.select_lang': 'Language',
    'common.loading': 'Loading...',
    'common.retry': 'Retry',
    'common.back': 'Back',
    'common.close': 'Close',
    'common.sync_now': 'Sync Now',
    'common.view_map': 'View on Map',
    'common.view_details': 'View Details',
    'common.view_alerts': 'View Active Alerts',
    'common.district': 'District',
    'common.station_id': 'Station ID',
    'common.updated': 'Updated',
    'common.valid_from': 'Valid From',
    'common.valid_until': 'Valid Until',
    'common.status': 'Status',
    
    // Homepage & Public UX
    'homepage.title': 'Is there a flood risk in your area today?',
    'homepage.subtitle': 'Real-time hydrological AI estimates & early warnings for Sri Lanka.',
    'homepage.select_area': 'Select Monitoring Area',
    'homepage.choose_location': 'Choose a station / area...',
    'homepage.current_risk': 'Current Flood Risk',
    'homepage.what_to_do': 'What To Do Now',
    'homepage.emergency_hotline': 'Emergency Disaster Hotline',
    'homepage.dmc_contact': 'Call DMC Hotline 117 for immediate emergency assistance and official disaster response.',
    'homepage.tech_drawer_title': 'Technical ML Model & Feature Specifications',
    'homepage.model_name': 'Model Name',
    'homepage.model_version': 'Model Version',
    'homepage.features_used': 'Hydro-Meteo Features',
    'homepage.prediction_id': 'Prediction Audit ID',

    // Risk Levels
    'risk.low': 'Low Risk',
    'risk.moderate': 'Moderate Risk',
    'risk.high': 'High Risk',
    'risk.critical': 'Critical Risk',
    'risk.low_short': 'LOW',
    'risk.mod_short': 'MOD',
    'risk.high_short': 'HIGH',
    'risk.crit_short': 'CRIT',

    // Action Codes
    'action.safe': 'Normal conditions. No immediate flood risk detected.',
    'action.monitor': 'Monitor local water levels and weather updates.',
    'action.prepare': 'Prepare emergency supplies and move valuables to high ground.',
    'action.evacuate': 'Immediate evacuation or move to high ground advised.',

    // Conditions & Telemetry
    'cond.rainfall_24h': '24h Rainfall',
    'cond.water_level': 'Water Level / Discharge',
    'cond.water_trend': 'Water Level Trend',
    'cond.temperature': 'Temperature',
    'cond.humidity': 'Humidity',

    // Operational States
    'state.current': 'CURRENT',
    'state.stale': 'STALE',
    'state.missing': 'NO PREDICTION RECORDED',
    'state.error': 'UNABLE TO LOAD RISK DATA',
    'state.stale_banner': 'This prediction may be outdated. Next update cycle pending.',
    'state.missing_banner': 'No current flood prediction is recorded for this location.',
    'state.error_banner': 'The prediction server could not be reached.',

    // Alerts System
    'alerts.title': 'Flood Alerts System',
    'alerts.active_count': 'Active Area Alerts',
    'alerts.official_vs_ml': 'ML estimates provide early data guidance; official warnings originate from the DMC/Irrigation Department.',
    'alerts.issued_at': 'Issued At',
    'alerts.expires_at': 'Expires At',
    'alerts.no_active': 'No active flood alerts reported for this area.',

    // History System
    'history.title': 'Historical Prediction Records',
    'history.subtitle': 'Immutable audit log of recorded predictions for this location.',
    'history.table_date': 'Date & Time',
    'history.table_prob': 'Probability',
    'history.table_risk': 'Risk Level',
    'history.table_action': 'Action Recommended',
    'history.empty': 'No historical prediction logs recorded for this station.',

    // Flood Map
    'map.title': 'Sri Lanka Flood Risk Map',
    'map.legend': 'Flood Risk Legend',
    'map.click_station': 'Click any station marker for detailed catchment telemetry.',
    
    // Official Notice & Warnings
    'official.warning_title': 'Official Government Warning',
    'official.notice_title': 'Official Warning Notice',
    'official.no_warning': 'No active official government warning for this area.',
    'official.unavailable': 'Official warning information is temporarily unavailable.',
    'official.expired': 'This official government warning has expired.',
    'official.issued_by': 'Issuing Authority',
    'official.issued_at': 'Issued At',
    'official.valid_until': 'Valid Until',
    'official.ref': 'Official Reference',
    'official.view_source': 'View Official Source',
    'official.disclaimer': 'This flood-risk estimate is calculated by Machine Learning models. Official government evacuation orders and advisories are issued by DMC 117.',

    // Safety Guidance
    'safety.title': 'Official Safety & Emergency Guidance',
    'safety.subtitle': 'Follow verified government safety guidelines during heavy rainfall and flood alerts.',
    'safety.emergency_hotline': 'Emergency Assistance',
    'safety.dmc_117': 'Call DMC 117',
    'safety.tip1': 'Move to designated high ground or evacuation shelters immediately if water levels rise.',
    'safety.tip2': 'Keep emergency kit ready with drinking water, dry food, essential medicines, and flashlight.',
    'safety.tip3': 'Never attempt to walk, swim, or drive through fast-flowing floodwaters.',
    'safety.tip4': 'Stay tuned to official Disaster Management Centre (DMC 117) radio and news broadcasts.',

    // Emergency Mode & Low-Bandwidth
    'emergency.title': 'Low-Bandwidth & Emergency Mode',
    'emergency.subtitle': 'Simplified, high-reliability flood risk & official warning interface.',
    'emergency.mode_active': 'Emergency Mode Active',
    'emergency.switch_normal': 'Normal Mode',
    'emergency.switch_emergency': 'Low-Bandwidth Mode',
    'emergency.last_known_banner': 'Displaying last available flood-risk estimate. Current live information could not be retrieved.',
    'emergency.stale_banner': 'This cached information may be outdated. Next update cycle pending.',
    'emergency.unavailable_title': 'Current flood-risk information is unavailable.',
    'emergency.unavailable_msg': 'Please check your connection and try again, or call DMC Hotline 117 for immediate emergency status.',
    'emergency.partial_prediction_failed': 'ML flood-risk estimate is temporarily unavailable.',
    'emergency.partial_warning_failed': 'Official government warning service could not be reached.',
    'emergency.net_status': 'Network Status',
    'emergency.net_online': 'ONLINE',
    'emergency.net_slow': 'SLOW CONNECTION',
    'emergency.net_offline': 'OFFLINE',
    'emergency.net_unavailable': 'SERVER UNAVAILABLE',
    'emergency.net_recovering': 'RECONNECTING...'
  },

  si: {
    // Navigation & General UI
    'nav.home': 'සජීවී පුවරුව',
    'nav.map': 'ගංවතුර සිතියම',
    'nav.details': 'ස්ථාන විස්තර',
    'nav.alerts': 'අනතුරු ඇඟවීම් සහ ඉතිහාසය',
    'nav.select_lang': 'භාෂාව',
    'common.loading': 'පූරණය වෙමින් පවතී...',
    'common.retry': 'නැවත උත්සාහ කරන්න',
    'common.back': 'ආපසු',
    'common.close': 'වසා දමන්න',
    'common.sync_now': 'දැන් යාවත්කාලීන කරන්න',
    'common.view_map': 'සිතියම බලන්න',
    'common.view_details': 'විස්තර බලන්න',
    'common.view_alerts': 'අනතුරු ඇඟවීම් බලන්න',
    'common.district': 'දිස්ත්‍රික්කය',
    'common.station_id': 'ස්ථාන අංකය',
    'common.updated': 'යාවත්කාලීන කළේ',
    'common.valid_from': 'වලංගු ආරම්භය',
    'common.valid_until': 'වලංගු අවසානය',
    'common.status': 'තත්ත්වය',
    
    // Homepage & Public UX
    'homepage.title': 'අද ඔබේ ප්‍රදේශයේ ගංවතුර අවදානමක් තිබේද?',
    'homepage.subtitle': 'ශ්‍රී ලංකාව සඳහා තථ්‍ය කාලීන ජල විද්‍යාත්මක AI ගංවතුර පූර්ව අනතුරු ඇඟවීම්.',
    'homepage.select_area': 'නිරීක්ෂණ ප්‍රදේශය තෝරන්න',
    'homepage.choose_location': 'ස්ථානයක් / ප්‍රදේශයක් තෝරන්න...',
    'homepage.current_risk': 'වත්මන් ගංවතුර අවදානම',
    'homepage.what_to_do': 'දැන් කළ යුතු දේ',
    'homepage.emergency_hotline': 'ආපදා හදිසි ඇමතුම් අංකය',
    'homepage.dmc_contact': 'හදිසි සහන සහ නිල ආපදා තොරතුරු සඳහා ආපදා කළමනාකරණ මධ්‍යස්ථානයේ 117 අමතන්න.',
    'homepage.tech_drawer_title': 'තාක්ෂණික AI ආකෘති විස්තර',
    'homepage.model_name': 'ආකෘති නාමය',
    'homepage.model_version': 'ආකෘති අනුවාදය',
    'homepage.features_used': 'ජල-කාලගුණික සාධක',
    'homepage.prediction_id': 'අනාවැකි වාර්තා අංකය',

    // Risk Levels
    'risk.low': 'අඩු අවදානම',
    'risk.moderate': 'මධ්‍යම අවදානම',
    'risk.high': 'ඉහළ අවදානම',
    'risk.critical': 'අතිශය අවදානම්',
    'risk.low_short': 'අඩු',
    'risk.mod_short': 'මධ්‍යම',
    'risk.high_short': 'ඉහළ',
    'risk.crit_short': 'අතිශය',

    // Action Codes
    'action.safe': 'සාමාන්‍ය තත්ත්වය. ක්ෂණික ගංවතුර අවදානමක් නැත.',
    'action.monitor': 'ප්‍රදේශයේ ජල මට්ටම් සහ කාලගුණ වාර්තා සලකා බලන්න.',
    'action.prepare': 'අත්‍යවශ්‍ය ද්‍රව්‍ය සූදානම් කර වටිනා දෑ උස් ස්ථාන වෙත ගෙන යන්න.',
    'action.evacuate': 'වහාම ආරක්ෂිත උස් ස්ථාන වෙත ඉවත් වන්න.',

    // Conditions & Telemetry
    'cond.rainfall_24h': 'පැය 24 වර්ෂාපතනය',
    'cond.water_level': 'ජල මට්ටම / පිටාර ප්‍රමාණය',
    'cond.water_trend': 'ජල මට්ටමේ ප්‍රවණතාව',
    'cond.temperature': 'උෂ්ණත්වය',
    'cond.humidity': 'ආර්ද්‍රතාව',

    // Operational States
    'state.current': 'වත්මන්',
    'state.stale': 'කල් ඉකුත් වූ',
    'state.missing': 'අනාවැකි සටහන් වී නැත',
    'state.error': 'තොරතුරු ලබාගත නොහැක',
    'state.stale_banner': 'මෙම තොරතුරු කල් ඉකුත් වී තිබිය හැක. ඊළඟ යාවත්කාලීන කිරීම අපේක්ෂාවෙන්.',
    'state.missing_banner': 'මෙම ස්ථානය සඳහා වත්මන් ගංවතුර අනාවැකියක් සටහන් වී නොමැත.',
    'state.error_banner': 'අනාවැකි සේවාදායකය හා සම්බන්ධ විය නොහැකි විය.',

    // Alerts System
    'alerts.title': 'ගංවතුර අනතුරු ඇඟවීමේ පද්ධතිය',
    'alerts.active_count': 'සක්‍රිය අනතුරු ඇඟවීම්',
    'alerts.official_vs_ml': 'AI අනාවැකි පූර්ව දැනුවත් කිරීම් සඳහා වන අතර නිල අනතුරු ඇඟවීම් DMC/වාරිමාර්ග දෙපාර්තමේන්තුවෙන් නිකුත් වේ.',
    'alerts.issued_at': 'නිකුත් කළ වේලාව',
    'alerts.expires_at': 'අවසාන වේලාව',
    'alerts.no_active': 'මෙම ප්‍රදේශය සඳහා සක්‍රිය ගංවතුර අනතුරු ඇඟවීම් නොමැත.',

    // History System
    'history.title': 'ඓතිහාසික අනාවැකි වාර්තා',
    'history.subtitle': 'මෙම ස්ථානය සඳහා සටහන් වූ අතීත අනාවැකි සටහන්.',
    'history.table_date': 'දිනය සහ වේලාව',
    'history.table_prob': 'සම්භාවිතාව',
    'history.table_risk': 'අවදානම් මට්ටම',
    'history.table_action': 'නිර්දේශිත ක්‍රියාමාර්ගය',
    'history.empty': 'මෙම ස්ථානය සඳහා අතීත අනාවැකි සටහන් වී නොමැත.',

    // Flood Map
    'map.title': 'ශ්‍රී ලංකා ගංවතුර අවදානම් සිතියම',
    'map.legend': 'අවදානම් සංකේත විස්තරය',
    'map.click_station': 'වැඩිදුර විස්තර සඳහා සිතියමේ ස්ථාන ලකුණක් මත ක්ලික් කරන්න.',

    // Official Notice & Warnings
    'official.warning_title': 'නිල රජයේ අනතුරු ඇඟවීම',
    'official.notice_title': 'නිල නිවේදනය',
    'official.no_warning': 'මෙම ප්‍රදේශය සඳහා සක්‍රිය නිල රජයේ අනතුරු ඇඟවීමක් නොමැත.',
    'official.unavailable': 'නිල අනතුරු ඇඟවීමේ තොරතුරු තාවකාලිකව ලබාගත නොහැක.',
    'official.expired': 'මෙම නිල රජයේ අනතුරු ඇඟවීම කල් ඉකුත් වී ඇත.',
    'official.issued_by': 'නිකුත් කළ අධිකාරිය',
    'official.issued_at': 'නිකුත් කළේ',
    'official.valid_until': 'වලංගු අවසානය',
    'official.ref': 'නිල වාර්තා අංකය',
    'official.view_source': 'නිල මූලාශ්‍රය බලන්න',
    'official.disclaimer': 'මෙම ගංවතුර තක්සේරුව කෘතිම බුද්ධි ආකෘති මගින් ගණනය කෙරේ. නිල ඉවත් කිරීමේ නියෝග සහ රජයේ නිවේදන DMC 117 මගින් නිකුත් වේ.',

    // Safety Guidance
    'safety.title': 'නිල ආරක්ෂක සහ හදිසි උපදෙස්',
    'safety.subtitle': 'අධික වර්ෂාපතන සහ ගංවතුර අවස්ථාවලදී නිල ආරක්ෂක උපදෙස් අනුගමනය කරන්න.',
    'safety.emergency_hotline': 'හදිසි සහන සේවාව',
    'safety.dmc_117': 'DMC 117 ඇමතුම',
    'safety.tip1': 'ජල මට්ටම ඉහළ යන්නේ නම් වහාම ආරක්ෂිත උස් ස්ථාන වෙත හෝ සහන මධ්‍යස්ථාන වෙත යන්න.',
    'safety.tip2': 'පිරිසිදු ජලය, වියළි ආහාර, ඖෂධ සහ විදුලි පන්දම් සහිත හදිසි කට්ටලයක් සූදානම් කර තබා ගන්න.',
    'safety.tip3': 'ගලා බසින ගංවතුර හරහා ගමන් කිරීමෙන් හෝ වාහන පැදවීමෙන් වළකින්න.',
    'safety.tip4': 'ආපදා කළමනාකරණ මධ්‍යස්ථානයේ (DMC 117) නිල නිවේදනවලට නිරන්තරයෙන් සවන් දෙන්න.',

    // Emergency Mode & Low-Bandwidth
    'emergency.title': 'අඩු කලාප පළල සහ හදිසි ප්‍රකාරය',
    'emergency.subtitle': 'සරල කළ, ඉහළ විශ්වාසනීයත්වයකින් යුත් ගංවතුර පූර්ව අනතුරු ඇඟවීම් පද්ධතිය.',
    'emergency.mode_active': 'හදිසි ප්‍රකාරය සක්‍රියයි',
    'emergency.switch_normal': 'සාමාන්‍ය ප්‍රකාරය',
    'emergency.switch_emergency': 'අඩු දත්ත ප්‍රකාරය',
    'emergency.last_known_banner': 'අවසාන ලබාගත හැකි ගංවතුර අවදානම් තක්සේරුව පෙන්වයි. සජීවී තොරතුරු ලබාගැනීමට නොහැකි විය.',
    'emergency.stale_banner': 'මෙම තොරතුරු කල් ඉකුත් වී තිබිය හැක. ඊළඟ යාවත්කාලීනය අපේක්ෂාවෙන්.',
    'emergency.unavailable_title': 'වත්මන් ගංවතුර අවදානම් තොරතුරු ලබාගත නොහැක.',
    'emergency.unavailable_msg': 'කරුණාකර සම්බන්ධතාවය පරීක්ෂා කර නැවත උත්සාහ කරන්න, නැතහොත් ක්ෂණික තොරතුරු සඳහා DMC 117 අමතන්න.',
    'emergency.partial_prediction_failed': 'AI ගංවතුර අවදානම් තක්සේරුව තාවකාලිකව ලබාගත නොහැක.',
    'emergency.partial_warning_failed': 'නිල රජයේ අනතුරු ඇඟවීමේ සේවාවට සම්බන්ධ විය නොහැකි විය.',
    'emergency.net_status': 'ජාල තත්ත්වය',
    'emergency.net_online': 'සක්‍රියයි',
    'emergency.net_slow': 'මන්දගාමී ජාලය',
    'emergency.net_offline': 'විසන්ධි වී ඇත',
    'emergency.net_unavailable': 'සේවාදායකය ලබාගත නොහැක',
    'emergency.net_recovering': 'නැවත සම්බන්ධ වෙමින්...'
  },

  ta: {
    // Navigation & General UI
    'nav.home': 'நேரலை டாஷ்போர்டு',
    'nav.map': 'வெள்ள வரைபடம்',
    'nav.details': 'இட விவரங்கள்',
    'nav.alerts': 'எச்சரிக்கைகள் & வரலாறு',
    'nav.select_lang': 'மொழி',
    'common.loading': 'ஏற்றப்படுகிறது...',
    'common.retry': 'மீண்டும் முயற்சிக்கவும்',
    'common.back': 'பின்னால்',
    'common.close': 'மூடு',
    'common.sync_now': 'இப்போது புதுப்பிக்கவும்',
    'common.view_map': 'வரைபடத்தில் பார்க்கவும்',
    'common.view_details': 'விவரங்களைப் பார்க்கவும்',
    'common.view_alerts': 'எச்சரிக்கைகளைப் பார்க்கவும்',
    'common.district': 'மாவட்டம்',
    'common.station_id': 'நிலையம் ID',
    'common.updated': 'புதுப்பிக்கப்பட்டது',
    'common.valid_from': 'செல்லுபடியாகும் தொடக்கம்',
    'common.valid_until': 'செல்லுபடியாகும் முடிவு',
    'common.status': 'நிலை',
    
    // Homepage & Public UX
    'homepage.title': 'இன்று உங்கள் பகுதியில் வெள்ள அபாயம் உள்ளதா?',
    'homepage.subtitle': 'இலங்கைக்கான நேரலை நீர்நிலவியல் AI வெள்ள முன்எச்சரிக்கைகள்.',
    'homepage.select_area': 'கண்காணிப்பு பகுதியைத் தேர்ந்தெடுக்கவும்',
    'homepage.choose_location': 'ஒரு நிலையைத் தேர்ந்தெடுக்கவும்...',
    'homepage.current_risk': 'தற்போதைய வெள்ள அபாயம்',
    'homepage.what_to_do': 'இப்போது என்ன செய்ய வேண்டும்',
    'homepage.emergency_hotline': 'அவசர ஆபத்து உதவி எண்',
    'homepage.dmc_contact': 'அவசர உதவி மற்றும் அதிகாரப்பூர்வ பேரிடர் தகவலுக்கு DMC உதவி எண் 117 ஐ அழைக்கவும்.',
    'homepage.tech_drawer_title': 'தொழில்நுட்ப AI மாதிரி விவரங்கள்',
    'homepage.model_name': 'மாதிரி பெயர்',
    'homepage.model_version': 'மாதிரி பதிப்பு',
    'homepage.features_used': 'நீர்-வானிலை காரணிகள்',
    'homepage.prediction_id': 'முன்கணிப்பு பதிவு ID',

    // Risk Levels
    'risk.low': 'குறைந்த ஆபத்து',
    'risk.moderate': 'மிதமான ஆபத்து',
    'risk.high': 'அதிக ஆபத்து',
    'risk.critical': 'மிகவும் தீவிரமான ஆபத்து',
    'risk.low_short': 'குறைந்த',
    'risk.mod_short': 'மிதமான',
    'risk.high_short': 'அதிக',
    'risk.crit_short': 'தீவிரமான',

    // Action Codes
    'action.safe': 'இயல்பு நிலை. உடனடி வெள்ள ஆபத்து இல்லை.',
    'action.monitor': 'உள்ளூர் நீர் நிலைகள் மற்றும் வானிலை அறிக்கைகளைக் கவனியுங்கள்.',
    'action.prepare': 'அவசரப் பொருட்களைத் தயார் செய்து, மதிப்புமிக்க பொருட்களை உயரமான இடங்களுக்கு மாற்றவும்.',
    'action.evacuate': 'உடனடியாக வெளியேறி பாதுகாப்பான உயரமான இடங்களுக்கு செல்லவும்.',

    // Conditions & Telemetry
    'cond.rainfall_24h': '24 மணி மழைப்பொழிவு',
    'cond.water_level': 'நீர் மட்டம் / வெளியேற்றம்',
    'cond.water_trend': 'நீர் மட்ட போக்கு',
    'cond.temperature': 'வெப்பநிலை',
    'cond.humidity': 'ஈரப்பதம்',

    // Operational States
    'state.current': 'தற்போதைய',
    'state.stale': 'பழைய தரவு',
    'state.missing': 'முன்கணிப்பு பதிவு செய்யப்படவில்லை',
    'state.error': 'தரவை ஏற்ற முடியவில்லை',
    'state.stale_banner': 'இந்தத் தகவல் காலாவதியாகி இருக்கலாம். அடுத்த புதுப்பிப்பு நிலுவையில் உள்ளது.',
    'state.missing_banner': 'இந்த இடத்திற்கு தற்போதைய வெள்ள முன்கணிப்பு எதுவும் பதிவு செய்யப்படவில்லை.',
    'state.error_banner': 'முன்கணிப்பு சேவையகத்தை தொடர்பு கொள்ள முடியவில்லை.',

    // Alerts System
    'alerts.title': 'வெள்ள எச்சரிக்கை அமைப்பு',
    'alerts.active_count': 'செயலில் உள்ள எச்சரிக்கைகள்',
    'alerts.official_vs_ml': 'AI கணிப்புகள் வழிகாட்டுதலுக்கு மட்டுமே; அதிகாரப்பூர்வ எச்சரிக்கைகள் DMC/நீர்ப்பாசனத் துறையால் வழங்கப்படுகின்றன.',
    'alerts.issued_at': 'வெளியிடப்பட்ட நேரம்',
    'alerts.expires_at': 'காலாவதியாகும் நேரம்',
    'alerts.no_active': 'இந்தப் பகுதிக்கு செயலில் உள்ள வெள்ள எச்சரிக்கைகள் எதுவும் இல்லை.',

    // History System
    'history.title': 'வரலாற்று முன்கணிப்பு பதிவுகள்',
    'history.subtitle': 'இந்த இடத்திற்கான கடந்தகால முன்கணிப்பு பதிவுகள்.',
    'history.table_date': 'தேதி & நேரம்',
    'history.table_prob': 'சாத்தியக்கூறு',
    'history.table_risk': 'ஆபத்து நிலை',
    'history.table_action': 'பரிந்துரைக்கப்பட்ட நடவடிக்கை',
    'history.empty': 'இந்த நிலையத்திற்கு வரலாற்று முன்கணிப்பு பதிவுகள் எதுவும் இல்லை.',

    // Flood Map
    'map.title': 'இலங்கை வெள்ள அபாய வரைபடம்',
    'map.legend': 'அபாயக் குறியீட்டு விளக்கம்',
    'map.click_station': 'கூடுதல் விவரங்களுக்கு வரைபடத்தில் உள்ள எந்த நிலையத்தையும் கிளிக் செய்யவும்.',

    // Official Notice & Warnings
    'official.warning_title': 'அதிகாரப்பூர்வ அரசு எச்சரிக்கை',
    'official.notice_title': 'அதிகாரப்பூர்வ அறிவிப்பு',
    'official.no_warning': 'இந்தப் பகுதிக்கு செயலில் உள்ள அதிகாரப்பூர்வ அரசு எச்சரிக்கை எதுவும் இல்லை.',
    'official.unavailable': 'அதிகாரப்பூர்வ எச்சரிக்கை தகவலைத் தற்காலிகமாகப் பெற முடியவில்லை.',
    'official.expired': 'இந்த அதிகாரப்பூர்வ அரசு எச்சரிக்கை காலாவதியாகிவிட்டது.',
    'official.issued_by': 'வெளியிட்ட அதிகாரம்',
    'official.issued_at': 'வெளியிடப்பட்ட நேரம்',
    'official.valid_until': 'செல்லுபடியாகும் நேரம்',
    'official.ref': 'அதிகாரப்பூர்வ குறிப்பு',
    'official.view_source': 'அதிகாரப்பூர்வ மூலத்தைப் பார்க்கவும்',
    'official.disclaimer': 'இந்த வெள்ள மதிப்பீடு AI மாதிரிகளால் கணக்கிடப்படுகிறது. அதிகாரப்பூர்வ வெளியேற்ற உத்தரவுகள் DMC 117 மூலம் வழங்கப்படுகின்றன.',

    // Safety Guidance
    'safety.title': 'அதிகாரப்பூர்வ பாதுகாப்பு வழிகாட்டுதல்கள்',
    'safety.subtitle': 'கனமழை மற்றும் வெள்ள எச்சரிக்கைகளின் போது அரசு பாதுகாப்பு வழிகாட்டுதல்களைப் பின்தொடரவும்.',
    'safety.emergency_hotline': 'அவசர உதவி',
    'safety.dmc_117': 'DMC 117 அழைக்கவும்',
    'safety.tip1': 'நீர் மட்டம் உயர்ந்தால் உடனடியாக பாதுகாப்பான உயரமான இடங்கள் அல்லது நிவாரண மையங்களுக்குச் செல்லவும்.',
    'safety.tip2': 'குடிநீர், உலர் உணவு, அத்தியாவசிய மருந்துகள் மற்றும் டார்ச் லைட் அடங்கிய அவசரப் பெட்டியைத் தயார் நிலையில் வைத்திருக்கவும்.',
    'safety.tip3': 'வேகமாக ஓடும் வெள்ள நீரில் ஒருபோதும் நடக்கவோ, நீந்தவோ அல்லது வாகனம் ஓட்டவோ வேண்டாம்.',
    'safety.tip4': 'பேரிடர் மேலாண்மை மையத்தின் (DMC 117) அதிகாரப்பூர்வ அறிவிப்புகளைப் பின்தொடரவும்.',

    // Emergency Mode & Low-Bandwidth
    'emergency.title': 'குறைந்த அலைவரிசை & அவசர முறை',
    'emergency.subtitle': 'எளிமையாக்கப்பட்ட, அதிக நம்பகத்தன்மை கொண்ட வெள்ள எச்சரிக்கை இடைமுகம்.',
    'emergency.mode_active': 'அவசர முறை செயலில் உள்ளது',
    'emergency.switch_normal': 'சாதாரண முறை',
    'emergency.switch_emergency': 'குறைந்த தரவு முறை',
    'emergency.last_known_banner': 'கடைசியாகக் கிடைத்த வெள்ள அபாய மதிப்பீட்டைக் காட்டுகிறது. நேரலைத் தகவலைப் பெற முடியவில்லை.',
    'emergency.stale_banner': 'இந்தத் தகவல் காலாவதியாகியிருக்கலாம். அடுத்த புதுப்பிப்பிற்காகக் காத்திருக்கிறது.',
    'emergency.unavailable_title': 'தற்போதைய வெள்ள அபாயத் தகவல் கிடைக்கவில்லை.',
    'emergency.unavailable_msg': 'உங்கள் இணைப்பைச் சரிபார்த்து மீண்டும் முயற்சிக்கவும், அல்லது உடனடி அவசர நிலைக்கு DMC உதவி எண் 117 ஐ அழைக்கவும்.',
    'emergency.partial_prediction_failed': 'AI வெள்ள அபாய மதிப்பீடு தற்காலிகமாகக் கிடைக்கவில்லை.',
    'emergency.partial_warning_failed': 'அதிகாரப்பூர்வ அரசு எச்சரிக்கை சேவையைத் தொடர்பு கொள்ள முடியவில்லை.',
    'emergency.net_status': 'பிணைய நிலை',
    'emergency.net_online': 'இணைக்கப்பட்டுள்ளது',
    'emergency.net_slow': 'மெதுவான இணைப்பு',
    'emergency.net_offline': 'இணைப்பு துண்டிக்கப்பட்டது',
    'emergency.net_unavailable': 'சேவையகம் கிடைக்கவில்லை',
    'emergency.net_recovering': 'மீண்டும் இணைக்கப்படுகிறது...'
  },
};

// Localized place names for Sri Lankan monitoring stations (presentation layer only)
const localizedLocations = {
  1: { en: 'Kolonnawa', si: 'කොලොන්නාව', ta: 'கொலன்னாவ' },
  2: { en: 'Hanwella', si: 'හංවැල්ල', ta: 'ஹன்வெல்ல' },
  3: { en: 'Glencorse', si: 'ග්ලෙන්කෝස්', ta: 'கிளென்கோர்ஸ்' },
  4: { en: 'Deraniyagala', si: 'දෙරණියගල', ta: 'தெரணியகல' },
  5: { en: 'Kitulgala', si: 'කිතුල්ගල', ta: 'கித்துல்கல' },
  6: { en: 'Holombuwa', si: 'හොලොම්බුව', ta: 'ஹொலொம்புவ' },
  7: { en: 'Ratnapura', si: 'රත්නපුරය', ta: 'இரத்தினபுரி' },
  8: { en: 'Ellagawa', si: 'ඇල්ලගාව', ta: 'எல்லகாவ' },
  9: { en: 'Magura', si: 'මගුර', ta: 'மகுர' },
  10: { en: 'Baddegama', si: 'බද්දේගම', ta: 'பத்தேகம' },
  11: { en: 'Thawalama', si: 'තවලම', ta: 'தவலம' },
  12: { en: 'Panadugama', si: 'පනාඩුගම', ta: 'பனாடுகம' },
  13: { en: 'Kandy', si: 'මහනුවර', ta: 'கண்டி' },
  14: { en: 'Peradeniya', si: 'පේරාදෙණිය', ta: 'பேராதனை' },
  15: { en: 'Nawalapitiya', si: 'නාවලපිටිය', ta: 'நாவலப்பிட்டி' },
  16: { en: 'Gampola', si: 'ගම්පොළ', ta: 'கம்பளை' },
  17: { en: 'Teldeniya', si: 'තෙල්දෙණිය', ta: 'தெல்தெனிய' },
  18: { en: 'Matara', si: 'මාතර', ta: 'மாத்தறை' },
  19: { en: 'Galle', si: 'ගාල්ල', ta: 'காலி' },
  20: { en: 'Kalutara', si: 'කළුතර', ta: 'களுத்துறை' },
  21: { en: 'Gampaha', si: 'ගම්පහ', ta: 'கம்பஹா' },
  22: { en: 'Ja-Ela', si: 'ජා-ඇල', ta: 'ஜா-எல' },
  23: { en: 'Kurunegala', si: 'කුරුණෑගල', ta: 'குருணாகல்' },
  24: { en: 'Puttalam', si: 'පුත්තලම', ta: 'புத்தளம்' },
  25: { en: 'Chilaw', si: 'හලාවත', ta: 'சிலாபம்' },
  26: { en: 'Anuradhapura', si: 'අනුරාධපුරය', ta: 'அனுராதபுரம்' },
  27: { en: 'Polonnaruwa', si: 'පොළොන්නරුව', ta: 'பொலன்னறுவை' },
  28: { en: 'Trincomalee', si: 'ත්‍රිකුණාමලය', ta: 'திருகோணமலை' },
  29: { en: 'Batticaloa', si: 'මඩකලපුව', ta: 'மட்டக்களப்பு' },
  30: { en: 'Ampara', si: 'අම්පාර', ta: 'அம்பாறை' },
  31: { en: 'Vavuniya', si: 'වවුනියාව', ta: 'வவுனியா' },
  32: { en: 'Kilinochchi', si: 'කිලිනොච්චිය', ta: 'கிளிநொச்சி' },
  33: { en: 'Jaffna', si: 'යාපනය', ta: 'யாழ்ப்பாணம்' }
};

class I18nEngine {
  constructor() {
    this.currentLang = this.resolveInitialLanguage();
    this.applyDocumentLang();
  }

  resolveInitialLanguage() {
    try {
      if (typeof window !== 'undefined') {
        const urlParams = new URLSearchParams(window.location.search);
        const urlLang = urlParams.get('lang');
        if (urlLang && SUPPORTED_LANGS.includes(urlLang.toLowerCase())) {
          return urlLang.toLowerCase();
        }
        const stored = localStorage.getItem(STORAGE_KEY);
        if (stored && SUPPORTED_LANGS.includes(stored.toLowerCase())) {
          return stored.toLowerCase();
        }
      }
    } catch (e) {}
    return DEFAULT_LANG;
  }

  getLanguage() {
    return this.currentLang;
  }

  setLanguage(lang) {
    if (!lang || !SUPPORTED_LANGS.includes(lang.toLowerCase())) return;
    const target = lang.toLowerCase();
    this.currentLang = target;
    
    try {
      if (typeof window !== 'undefined') {
        localStorage.setItem(STORAGE_KEY, target);
      }
    } catch (e) {}

    this.applyDocumentLang();

    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('floodwatch:language_changed', { detail: { language: target } }));
    }
  }

  applyDocumentLang() {
    if (typeof document !== 'undefined' && document.documentElement) {
      document.documentElement.lang = this.currentLang;
    }
  }

  t(key, params = {}) {
    const langDict = translations[this.currentLang] || translations[DEFAULT_LANG];
    let val = langDict[key] || translations[DEFAULT_LANG][key] || key;
    
    if (params && typeof params === 'object') {
      Object.keys(params).forEach(p => {
        val = val.replace(new RegExp(`\\{${p}\\}`, 'g'), params[p]);
      });
    }
    return val;
  }

  getRiskLabel(riskLevel) {
    const norm = (riskLevel || '').toUpperCase();
    if (norm === 'CRITICAL') return this.t('risk.critical');
    if (norm === 'HIGH') return this.t('risk.high');
    if (norm === 'MODERATE' || norm === 'MOD') return this.t('risk.moderate');
    return this.t('risk.low');
  }

  getRiskShortLabel(riskLevel) {
    const norm = (riskLevel || '').toUpperCase();
    if (norm === 'CRITICAL') return this.t('risk.crit_short');
    if (norm === 'HIGH') return this.t('risk.high_short');
    if (norm === 'MODERATE' || norm === 'MOD') return this.t('risk.mod_short');
    return this.t('risk.low_short');
  }

  getActionMessage(actionCode) {
    const norm = (actionCode || '').toUpperCase();
    if (norm === 'EVACUATE') return this.t('action.evacuate');
    if (norm === 'PREPARE') return this.t('action.prepare');
    if (norm === 'MONITOR') return this.t('action.monitor');
    return this.t('action.safe');
  }

  getLocationName(locationObj) {
    if (!locationObj) return 'Location';
    const locId = parseInt(locationObj.id || locationObj.location_id, 10);
    const placeMap = localizedLocations[locId];
    if (placeMap && placeMap[this.currentLang]) {
      return placeMap[this.currentLang];
    }
    return locationObj.place_name || locationObj.name || `Location #${locId || '1'}`;
  }

  validateTranslations() {
    const enKeys = Object.keys(translations.en);
    const missingInSi = enKeys.filter(k => !translations.si[k]);
    const missingInTa = enKeys.filter(k => !translations.ta[k]);
    return {
      total_keys: enKeys.length,
      en_status: 'PASS',
      si_status: missingInSi.length === 0 ? 'PASS' : 'FAIL',
      ta_status: missingInTa.length === 0 ? 'PASS' : 'FAIL',
      missing_si: missingInSi,
      missing_ta: missingInTa
    };
  }
}

export const i18n = new I18nEngine();

if (typeof window !== 'undefined') {
  window.floodWatchI18n = i18n;
}
