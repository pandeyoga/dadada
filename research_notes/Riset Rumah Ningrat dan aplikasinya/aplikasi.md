# Rumah Ningrat app(s): "Keluarga Ningrat" (Android/iOS) and the "Dashboard Warga Ningrat" customer web portal

Research date: 2026-11-23. All store metrics below were captured on 2026-11-23 from the live Google Play web page (Indonesia storefront, hl=id and hl=en, including Play's embedded page data), the iTunes Lookup API (country=id), the App Store web page, and rumahningrat.com / customer.rumahningrat.com. Store figures change over time.

Key URLs:
- Google Play: https://play.google.com/store/apps/details?id=com.trusmi.keluarganingrat
- Apple App Store: https://apps.apple.com/id/app/keluarganingrat/id6752388007 (lookup: https://itunes.apple.com/lookup?id=6752388007&country=id)
- Official site with download links: https://rumahningrat.com/
- Customer web portal: https://customer.rumahningrat.com/
- Play developer page: https://play.google.com/store/apps/developer?id=Trusmi+Group

## 1. Which app(s) exist?

### Takeaway
Rumah Ningrat's app is called **"Keluarga Ningrat"** (styled "KeluargaNingrat" on iOS), package/bundle ID `com.trusmi.keluarganingrat`, available on Google Play and the Indonesian App Store. There is also a separate customer **web portal** ("Dashboard Warga Ningrat", customer.rumahningrat.com). Searching store names for "Rumah Ningrat" alone does not surface the app well. No sales-agent, affiliate or reseller app was found.

### Cited Findings
- **Android app:** "Keluarga Ningrat", package `com.trusmi.keluarganingrat`, developer account "Trusmi Group", category House & Home, free. — [Google Play](https://play.google.com/store/apps/details?id=com.trusmi.keluarganingrat&hl=en&gl=ID)
- **iOS app:** "KeluargaNingrat", App Store ID 6752388007, bundle ID `com.trusmi.keluarganingrat` (same as Android), category Utilities, free. — [iTunes Lookup API](https://itunes.apple.com/lookup?id=6752388007&country=id); [App Store](https://apps.apple.com/id/app/keluarganingrat/id6752388007)
- The iTunes Search API (country=id, entity=software) returned **0 results** for "rumah ningrat", "rumahningrat", "ningrat" and "keluarga ningrat". The app was only found by its ID, which comes from the link on rumahningrat.com. — [iTunes Search API, "rumah ningrat"](https://itunes.apple.com/search?term=rumah+ningrat&country=id&entity=software); [iTunes Lookup](https://itunes.apple.com/lookup?id=6752388007&country=id)
- The iTunes Lookup with country=us returned 0 results, so the iOS app appears to be listed only in the Indonesian storefront. However, rumahningrat.com links to the US-path URL `apps.apple.com/us/app/keluarganingrat/id6752388007`. — [iTunes Lookup (us)](https://itunes.apple.com/lookup?id=6752388007&country=us); [rumahningrat.com](https://rumahningrat.com/)
- Google Play search for "rumah ningrat", "rumahningrat" and "ningrat" does return `com.trusmi.keluarganingrat`. — [Google Play search](https://play.google.com/store/search?q=rumah%20ningrat&c=apps&hl=id&gl=ID)
- The official site has a "Download Aplikasi" footer section and a "Keluarga Ningrat" section. Both link to the Play listing (`...id=com.trusmi.keluarganingrat&pcampaignid=web_share`) and the App Store listing. — [rumahningrat.com](https://rumahningrat.com/)
- **Web portal:** customer.rumahningrat.com, page title "Rumah Ningrat - Dashboard Warga Ningrat". The main site's nav links to it as "After Sales" (`?tab=aftersales`), "Pengajuan Komplain" (`?tab=komplain`) and "Cek Status KPR". — [customer.rumahningrat.com](https://customer.rumahningrat.com/); [rumahningrat.com](https://rumahningrat.com/)
- **Unrelated "Ningrat" apps from the same searches:**
  - "Ningrat Logistic" (`com.ningrat.logistic`) is by Infazio / PT. INFAZIO GLOBAL TECHNO in Jakarta. It is a driver/delivery-management app with 5+ downloads, updated Mar 10, 2026, and its "What's new" says "Initial Ningrat Logistic Apps by NIngrat Division". Nothing on the listing ties it to Rumah Ningrat. — [Google Play](https://play.google.com/store/apps/details?id=com.ningrat.logistic&hl=en&gl=ID)
  - "Rumah Berkarya Apps" (`com.rumahberkarya.portalkaryawan`, PT FLAVABOOKS RUMAH BERKARYA, Sukoharjo) is an unrelated employee portal. — [Google Play](https://play.google.com/store/apps/details?id=com.rumahberkarya.portalkaryawan&hl=en&gl=ID)

### Inferences
- The app is branded for the residents' community ("Keluarga Ningrat" means "Ningrat family"), not with the housing brand "Rumah Ningrat". That is likely why name searches for "Rumah Ningrat" on the App Store find nothing.
- Because the iOS Lookup fails for the US store, the US-path App Store link on the website may not open for some users, although Apple usually redirects to the local store.

### Gaps
- No subdomain enumeration was completed (the crt.sh query failed), so other web apps may exist, such as an agent or marketing portal.
- During the session the agent proxy reported a failed connection to `wp.rumahningrat.com`. That host exists in some form but was unreachable, and its purpose is unknown.
- No Rumah Ningrat app for sales agents, freelance marketers or referrers was found in the stores or on the website.

## 2. Publisher / developer, and in-house vs vendor

### Takeaway
The app is published under the Trusmi Group name, but the store accounts are registered to an individual, "Anggi Supriatna". Contact details point to Trusmi Group's IT team (ittrusmi@gmail.com) and to Rumah Ningrat's official phone number. The evidence suggests an in-house build by Trusmi Group IT, and no vendor or agency credit was found.

### Cited Findings
- **Google Play:**
  - Developer name: "Trusmi Group".
  - "About the developer" (legal name on the account): **Anggi Supriatna**, ittrusmi@gmail.com, Indonesia.
  - Support phone: +6281122887878. Support email: ittrusmi@gmail.com. Website: https://rumahningrat.com/.
  - The privacy-policy link points to `https://www.rumahningrat.com` (the homepage).
  - Source: [Google Play](https://play.google.com/store/apps/details?id=com.trusmi.keluarganingrat&hl=en&gl=ID)
- **Apple App Store:**
  - Seller/developer: **Anggi Supriatna** (artistId 1839195494).
  - Seller URL: https://rumahningrat.com/.
  - Copyright line: "© 2025 Trusmi Group. All rights reserved."
  - Source: [iTunes Lookup](https://itunes.apple.com/lookup?id=6752388007&country=id); [App Store](https://apps.apple.com/id/app/keluarganingrat/id6752388007)
- The Play support phone (+62 811-2288-7878) is the same number rumahningrat.com uses for WhatsApp (`wa.me/6281122887878`) and lists as "0811-2288-7878". The site footer gives the address Jl. Haji Abbas No.14 Trusmi, Kec. Weru, Cirebon, Jawa Barat. — [rumahningrat.com](https://rumahningrat.com/)
- **Other app from the same Play account:** "Trusmi OnTime" (`com.trusmiverse.trusmiontimes`), described as "Aplikasi absensi & HR modern dengan Face Recognition" (HR/attendance with face recognition and online/offline modes).
  - 1.000+ installs, rated 5.0 from 7 ratings, released 8 Jul 2026, website https://trusmigroup.com/.
  - The account lists only these two apps.
  - Source: [Play developer page](https://play.google.com/store/apps/developer?id=Trusmi+Group&hl=en&gl=ID); [Trusmi OnTime on Google Play](https://play.google.com/store/apps/details?id=com.trusmiverse.trusmiontimes&hl=id&gl=ID)
- A YouTube channel named "IT Trusmi Group" posted a video titled "JALAN UTAMA RUMAH NINGRAT KAYANGAN - 240831" (about 2 years old, 216 views when checked). This shows Trusmi Group's IT unit producing content about Rumah Ningrat estates. — [YouTube](https://www.youtube.com/watch?v=DeMVhhCrpJM)

### Inferences
- **In-house build (likely):** The package namespaces are `com.trusmi.*` and `com.trusmiverse.*`, the support email is an IT Trusmi Gmail address, and the account publishes only Trusmi apps (a residents' app and an internal HR app). There is no white-label vendor name and no multi-client developer account.
- The individual "Anggi Supriatna" is probably a Trusmi IT staff member whose personal developer account hosts the company apps. This is not verified.
- Publishing under an individual's account rather than a company-verified organization account matters for governance: app ownership is tied to one person.
- The website's Facebook link (`facebook.com/trusmiland.trusmiland.3`) suggests Rumah Ningrat sits under Trusmi Group's property arm, "Trusmi Land". That is not verified here, and the corporate profile is out of scope.

### Gaps
- There is no public statement naming the dev team or any vendor. Anggi Supriatna's role was not verified (no LinkedIn or press search was done).
- The tech stack was not determined. The iOS binary is 92 MB, but no framework was confirmed.

## 3. Purpose and audience

### Takeaway
Keluarga Ningrat is a **resident / estate-management "smart housing" app for people who live in Rumah Ningrat estates** (penghuni/warga). It is not a sales catalog or agent app. Pre-purchase and transaction tracking (KPR status, construction progress, payment history, complaints) are handled by the separate web portal, "Dashboard Warga Ningrat".

### Cited Findings
- The Play short description (English locale) says: "Keluarga Ningrat merupakan Apps yang diperuntukan bagi Warga Penghuni Rumah Ningrat dimanapun. Banyak fitur yang bisa digunakan dan dimanfaatkan." Its tagline is "Keluarga Ningrat, untuk Hidup Lebih baik." — [Google Play (en)](https://play.google.com/store/apps/details?id=com.trusmi.keluarganingrat&hl=en&gl=ID)
- The Play summary (Indonesian locale) says: "Aplikasi warga pintar: bayar IPL, CCTV, komplain & layanan hunian." The full description calls it "aplikasi digital untuk lingkungan hunian modern yang membantu warga mengakses berbagai layanan dalam satu aplikasi", built "untuk mendukung kebutuhan penghuni dan pengelola lingkungan". — [Google Play (id)](https://play.google.com/store/apps/details?id=com.trusmi.keluarganingrat&hl=id&gl=ID)
- The website says: "Aplikasi ini memudahkan kehidupan Anda di Perumahan Rumah Ningrat dengan fitur pemantauan CCTV, tombol SOS, dan berbagai layanan." — [rumahningrat.com](https://rumahningrat.com/)
- **Web portal (customer.rumahningrat.com, "Dashboard Warga Ningrat"):**
  - Its tagline reads: "Pantau Perjalanan Rumah Impian Anda di Sini. Cek status akad KPR, pantau progress pembangunan, riwayat pembayaran, hingga layanan komplain secara langsung dan transparan."
  - Login uses a KTP (national ID) number field ("Contoh: 3201234567890001", "*Pastikan Nomor KTP terdaftar").
  - It has a unit picker: "Nomor KTP Anda terdaftar di beberapa unit. Silakan pilih unit yang ingin Anda akses." Units are listed by project, blok and booking date.
  - Source: [customer.rumahningrat.com](https://customer.rumahningrat.com/)

### Inferences
- The two products cover different stages of the customer lifecycle:
  - **Buyer / pre-handover stage:** the web portal (KPR mortgage-approval status, construction progress, payment history, after-sales and complaints).
  - **Occupancy stage:** the mobile app (IPL fees, security, gate access, community, marketplace).
- The app also serves the estate manager ("pengelola lingkungan") as the back office for IPL billing, complaints and security rosters. Only the resident-facing side is published.
- In the HTML of the public login page, the portal form shows only a KTP-number field and no password field. If KTP alone grants access to KPR, payment and complaint data, that would be weak authentication, because KTP numbers are not secret. This was **not verified**: no login was attempted, and there may be a later OTP or other verification step.

### Gaps
- No evidence was found of the app or portal being used by internal staff beyond the estate manager, or by sales agents.
- The number of estates where the app's features are actually live (CCTV, smart gate) was not found.

## 4. Feature list

### Takeaway
The store listings describe 11 features: Marketplace, Ningrat Pay, IPL payment, Panic Button, Smart Main Gate, Live CCTV, Service Place, Hobby Community, Event Warga, Security On Duty and Complaint Management. The website promotes the security features (CCTV, SOS, one-gate) and the marketplace as selling benefits of buying a Rumah Ningrat house.

### Cited Findings
- **Google Play feature list (Indonesian):**
  - Marketplace: products and daily needs from tenants and local businesses in the estate.
  - Ningrat Pay: an integrated payment system for in-app services.
  - IPL (Iuran Pengelolaan Lingkungan): check bills and pay without visiting the management office.
  - Panic Button: emergency notification.
  - Smart Main Gate: gate access through the app.
  - Live CCTV: real-time view of estate cameras.
  - Service Place: find and order services such as home repair and cleaning.
  - Hobby Community: interest-based resident groups.
  - Event Warga: community events and programmes.
  - Security On Duty: shows which security guards are on duty.
  - Complaint Management: complaints and feedback to the estate manager, "lebih cepat dan transparan".
  - Source: [Google Play (id)](https://play.google.com/store/apps/details?id=com.trusmi.keluarganingrat&hl=id&gl=ID)
- **App Store:** the same 11 features under "FITUR UTAMA", plus "KEUNGGULAN": all estate needs in one app, real-time information, safe digital transactions, security, resident interaction and a simple interface. — [iTunes Lookup](https://itunes.apple.com/lookup?id=6752388007&country=id)
- **Website promotion on rumahningrat.com:**
  - "Fitur Live CCTV, Aplikasi Keluarga Ningrat – Keamanan terjaga melalui aplikasi Keluarga Ningrat, anda dapat memonitoring Live CCTV."
  - "GARANSI RUMAH AMAN – Fitur Live CCTV, hingga Security On Duty dapat diakses melalui Aplikasi Keluarga Ningrat."
  - "Kemajuan Ekonomi – Dukung peluang usaha dari rumah melalui aplikasi dan fitur Marketplace dari aplikasi Keluarga Ningrat."
  - "Fasilitas Keamanan – One gate system, serta Live CCTV setiap blok dan pengawasan 24 jam yang terintegrasi dalam satu aplikasi Keluarga Ningrat."
  - Source: [rumahningrat.com](https://rumahningrat.com/)
- The Play listing carries 8 unique screenshots, which were not visually reviewed. — [Google Play](https://play.google.com/store/apps/details?id=com.trusmi.keluarganingrat&hl=id&gl=ID)

### Inferences
- "Live CCTV setiap blok" and "Smart Main Gate" imply physical CCTV and gate hardware in the estates that is integrated with the app. Rollout probably varies by estate. This is not verified.

### Gaps
- No tutorial or promo videos about the app were found on YouTube. YouTube searches for "aplikasi keluarga ningrat", "rumah ningrat aplikasi" and "keluarga ningrat trusmi" returned no app-specific videos.
- Instagram (@rumahningrat_official) and TikTok (@rumahningratofficial) could not be checked for app posts, because content requires login.
- Payment rails behind Ningrat Pay (e-wallet, VA or payment gateway partner) are not disclosed anywhere found.

## 5. Metrics (as of 2026-11-23)

### Takeaway
The app is new and small. It has **1,000+ Android downloads**, no public rating on either store, and no reviews found. It was first published on iOS on 23 Nov 2025 and on Android in June 2026, and the Android app was updated as recently as 20 Nov 2026.

### Cited Findings
**Google Play (`com.trusmi.keluarganingrat`):**
- Installs: "1,000+". Play's embedded page data also carries an un-rounded install figure of 2,206, which is the field scraper tools report as "maxInstalls". It is approximate and not an official public number.
- Rating: none displayed, and no rating or review count is shown.
- Release date in the page data: 25 Jun 2026.
- Last updated: 20 Nov 2026 (timestamp 1795143194 = 2026-11-20 02:53 UTC).
- Current version: 1.0.11.
- Minimum Android: 7.0 (API 24). Target SDK: 36.
- Content rating: Rated 3+ ("Cocok untuk semua kelompok usia").
- Price: free. No "Contains ads" or "In-app purchases" label shown.
- Category: House & Home.
- Size: not shown on the Play web page.
- Source: [Google Play](https://play.google.com/store/apps/details?id=com.trusmi.keluarganingrat&hl=en&gl=ID)

**Google Play data safety (developer-declared):** "No data shared with third parties" and "No data collected". — [Google Play](https://play.google.com/store/apps/details?id=com.trusmi.keluarganingrat&hl=en&gl=ID)

**Apple App Store (ID 6752388007):**
- First release: 2025-11-23.
- Current version: 2.1, released 2026-06-29.
- Minimum iOS 13.0. iPhone only ("Only for iPhone").
- Size: 92,230,656 bytes (about 92.2 MB).
- Age rating: 4+. Genre: Utilities. Price: free.
- Language listed: English only, although the description is in Indonesian.
- Ratings: averageUserRating 0, userRatingCount 0. The App Store page says "This app has not received enough ratings or reviews to display an overview."
- Source: [iTunes Lookup](https://itunes.apple.com/lookup?id=6752388007&country=id); [App Store](https://apps.apple.com/id/app/keluarganingrat/id6752388007)

**App Store privacy label:** "Data Not Collected – The developer does not collect any data from this app" (self-reported by Anggi Supriatna and not verified by Apple). — [App Store](https://apps.apple.com/id/app/keluarganingrat/id6752388007)

**Comparison with the sister app:** Trusmi OnTime has 1.000+ installs and a 5.0 rating from 7 ratings. — [Google Play](https://play.google.com/store/apps/details?id=com.trusmiverse.trusmiontimes&hl=id&gl=ID)

### Inferences
- The "no data collected / not shared" declarations on both stores look **inconsistent with the advertised features**: IPL billing, Ningrat Pay transactions, complaints, panic-button alerts, and residents' unit/identity data all involve personal or financial data. The disclosures may be inaccurate or incomplete. This would need confirmation from the app's actual behaviour or its privacy policy.
- There is also no dedicated privacy-policy page: both stores point to the rumahningrat.com homepage.
- Version numbers differ across platforms: Android 1.0.11 versus iOS 2.1. The two builds may be maintained on separate version tracks.
- Android's 25 Jun 2026 "release" date falls within days of the iOS v2.x release (29 Jun 2026). This could mean the Android listing was created or re-published alongside v2. It is not verified.
- Against the website's claim of "10.000 Unit Terjual" ([rumahningrat.com](https://rumahningrat.com/)), 1,000–2,200 Android installs suggests a modest share of households have installed the app so far. This is a rough inference that ignores iOS installs, which are not public.

### Gaps
- iOS download counts are not public. Sensor Tower and data.ai estimates were not retrieved.
- AppBrain returned HTTP 403, so third-party Android version history was not obtained. APKPure and APKCombo were not checked.
- The Play app size was not obtained.

## 6. User reviews

### Takeaway
**No user reviews were found on either store.** The app has too few ratings to show a score on Google Play or the App Store, so there is no review sentiment to summarize.

### Cited Findings
- App Store: "This app has not received enough ratings or reviews to display an overview." userRatingCount = 0. — [App Store](https://apps.apple.com/id/app/keluarganingrat/id6752388007); [iTunes Lookup](https://itunes.apple.com/lookup?id=6752388007&country=id)
- Google Play shows no star rating or review count. Play's review data endpoint, queried for the Indonesia locale, returned an empty review list on 2026-11-23. — [Google Play](https://play.google.com/store/apps/details?id=com.trusmi.keluarganingrat&hl=id&gl=ID)

### Inferences
- With no store reviews, resident feedback on the app (if any) more likely sits in WhatsApp groups, Instagram or TikTok comments, or the in-app Complaint Management feature.

### Gaps
- Instagram, TikTok and Facebook comments about the app were not checked (login walls).
- Google Play reviews in other languages or locales were not individually queried.

## 7. Changelog / evolution

### Takeaway
The iOS app launched on 23 Nov 2025. The "Version 2.0.0" release notes (current iOS build 2.1, 29 Jun 2026) say six community, payment and service features were *added*: Ningrat Pay, Service Place, Hobby Community, Event Warga, Security On Duty and Complaint Management. That implies v1 covered a smaller core. Android has been updated regularly, most recently on 20 Nov 2026 (v1.0.11).

### Cited Findings
- The iOS release notes ("Version 2.0.0 – What's New") read:
  - "Added Ningrat Pay for easier digital payments"
  - "Added Service Place for booking and discovering local services"
  - "Added Hobby Community feature to connect residents with shared interests"
  - "Added Event Warga for community event information and participation"
  - "Added Security On Duty to view active security personnel information"
  - "Added Complaint Management for faster issue reporting and tracking"
  - Also performance, UI and bug-fix improvements.
  - Current iOS version is 2.1 (29 Jun 2026).
  - Source: [iTunes Lookup](https://itunes.apple.com/lookup?id=6752388007&country=id); [App Store](https://apps.apple.com/id/app/keluarganingrat/id6752388007)
- The Play listing's English-locale description is a short, older-style text ("...diperuntukan bagi Warga Penghuni Rumah Ningrat dimanapun..."). The Indonesian-locale description is the full 11-feature text. — [Google Play (en)](https://play.google.com/store/apps/details?id=com.trusmi.keluarganingrat&hl=en&gl=ID); [Google Play (id)](https://play.google.com/store/apps/details?id=com.trusmi.keluarganingrat&hl=id&gl=ID)
- Android: version 1.0.11, updated 20 Nov 2026. No "What's new" text appears on the page. — [Google Play](https://play.google.com/store/apps/details?id=com.trusmi.keluarganingrat&hl=id&gl=ID)

### Inferences
- By elimination from the v2.0.0 "Added" list, the v1 (Nov 2025) core was probably Marketplace, IPL, Panic Button, Smart Main Gate and Live CCTV. That matches the security- and marketplace-led messaging on the website. This is an inference and not stated anywhere.
- The direction of change is from a security/IPL utility toward a "super app" for residents: payments, services, community and complaints.

### Gaps
- No full version history was found for either platform. The App Store page shows only the latest notes, and AppBrain was blocked.

## 8. How it fits the business

### Takeaway
The app is positioned as a **differentiator in Rumah Ningrat's housing sales pitch**, which centres on subsidized and affordable houses in West and Central Java. On the website, "Live CCTV", "Security On Duty" and the marketplace sit beside free-fence and free-back-wall bonuses. The app also gives the developer and estate manager a digital channel for IPL collection, complaints and community management after handover.

### Cited Findings
- On rumahningrat.com the app appears in the "Benefit eksklusif" block next to "Benefit Gratis Pagar" and "Benefit Bonus Tembok Belakang Rumah", and under "GARANSI RUMAH AMAN". — [rumahningrat.com](https://rumahningrat.com/)
- The site shows projects in Bekasi, Cirebon, Kendal, Indramayu, Kuningan, Subang and Majalengka, and claims "32 Perumahan" and "10.000 Unit Terjual". An example listing is RN Jayasampurna, Bekasi, Rp 185.000.000. — [rumahningrat.com](https://rumahningrat.com/)
- A "Rumah Ningrat Official" YouTube video is titled "Rumah Ningrat adalah Perumahan Subsidi yang berdiri sejak tahun 2012 yang sudah tersedia di 7 Kota." (about 1 month old, 372 views when checked). — [YouTube](https://www.youtube.com/watch?v=VFsXUS_yVos)
- The web portal covers the pre-occupancy journey: KPR akad status, construction progress, payment history, after-sales and complaints. — [customer.rumahningrat.com](https://customer.rumahningrat.com/)

### Inferences
- Together, the portal and app form a buyer-to-resident lifecycle stack built by the group's IT team. The app supports (a) sales marketing ("safe housing" with CCTV), (b) recurring revenue and administration (IPL collection, Ningrat Pay) and (c) customer service (complaints), and may reduce after-sales friction.
- The marketplace and "peluang usaha dari rumah" messaging targets lower-to-middle-income residents of subsidized housing, encouraging home-based businesses within the estate.

### Gaps
- No data was found on IPL collection through the app, transaction volume, or how many estates have CCTV or smart-gate integration live.
- Whether app use is mandatory for residents, for example for IPL payment or gate access, is not documented.
