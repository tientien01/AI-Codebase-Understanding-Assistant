# AI Codebase Assistant - Stakeholder Requirements

Status: Accepted production v1 requirement detail  
Authority: Use-case scenarios and acceptance behavior; priorities and scope are owned by `../requirements-index.md` and `../scope-and-non-goals.md`  
Owner: Product owner  
Dependencies: `../requirements-index.md`, `../scope-and-non-goals.md`  
Related source: `../../14-implementation-baseline/`  
Related tests: requirement-linked API, security, UX, and E2E suites  
Last verified: 2026-07-12

Tai lieu nay mo ta cac yeu cau chuc nang that su can co cua AI Codebase Assistant duoi goc nhin stakeholder. Day la tai lieu doi chieu chinh khi quyet dinh mot tinh nang co nen duoc lam, lam den muc nao, va khi nao duoc xem la dat.

## Contract ownership and vocabulary

This document owns stakeholder goals, scenarios, and acceptance intent. `../requirements-index.md` owns current priority/scope; the data/indexing/API/security/UX contracts own exact state names, entities, wire schemas, authorization, limits, and failure semantics. Examples below must be read with these canonical rules:

- production v1 source inputs are browser folder upload, ZIP upload, and constrained public Git; backend-local path and private/arbitrary Git are not product inputs;
- repository lifecycle, import session, job/attempt, index lifecycle, source freshness, and capability readiness are separate;
- opaque `index_version_id` is identity; integer sequence is display/order only;
- capability states are `ready`, `limited`, `unavailable`, `failed`, or `stale`;
- Retrieval Candidate, Evidence, Citation, and Claim are separate;
- exact deterministic lookup precedes lexical/graph/optional semantic retrieval and bounded agent planning;
- build/job examples such as `completed_with_warnings` do not define capability readiness.

## 1. Muc tieu san pham

AI Codebase Assistant giup nguoi dung hieu nhanh mot codebase da co, dac biet khi codebase lon, la, hoac khong co tai lieu ro rang.

San pham khong chi la cong cu chat voi source code. San pham phai giup nguoi dung:

- Dua mot project vao he thong mot cach an toan.
- Biet project do gom nhung thanh phan nao.
- Tim duoc file, function, class, endpoint, va dependency quan trong.
- Dat cau hoi ve codebase va nhan cau tra loi co bang chung.
- Hieu tac dong khi sua mot phan code.
- Su dung Agentic AI de lap ke hoach kham pha codebase, chon tool phu hop, kiem tra evidence, va tao cau tra loi dang tin cay.
- Tu tin demo, kiem tra, va tiep tuc phat trien project.

## 2. Stakeholders

### Developer moi tham gia project

Nguoi nay can hieu codebase nhanh ma khong phai doc tung file.

Yeu cau:

- Xem duoc tong quan project.
- Biet tech stack that su cua project.
- Biet diem bat dau nen doc.
- Hoi duoc "module nay lam gi", "API nay o dau", "flow nay di qua nhung file nao".
- Cau tra loi phai co file, line, va doan code lam bang chung.

### Developer dang bao tri project

Nguoi nay can sua code ma khong gay loi ngoai y muon.

Yeu cau:

- Tim nhanh noi dinh nghia function, class, endpoint.
- Thay duoc dependency/import/call lien quan.
- Biet file nao co the bi anh huong khi sua mot file hoac symbol.
- Re-index duoc sau khi source code thay doi.
- Ket qua search/chat phai cap nhat theo lan index moi nhat.

### Tech lead hoac reviewer

Nguoi nay can danh gia cau truc, rui ro, va chat luong codebase.

Yeu cau:

- Xem tong quan kien truc project.
- Xem cac module/chuc nang chinh.
- Xem API surface neu project co backend.
- Xem cac diem phu thuoc phuc tap hoac kho bao tri.
- Co bang chung khi assistant dua ra nhan xet.

### Nguoi demo hoac cham diem project

Nguoi nay can thay chuong trinh hoat dong ro rang va on dinh.

Yeu cau:

- Import mot project mau thanh cong.
- Thay danh sach project ro rang, khong bi trung lap kho hieu.
- Mo workspace va xem thong tin co y nghia.
- Dat cau hoi va thay cau tra loi co citation.
- Xoa project test de lam sach du lieu demo.

## 3. Core user flows

### Flow 1: Dua project vao he thong

Nguoi dung co the them project bang cac cach sau:

- Upload folder.
- Upload file zip.
- Import GitHub repository trong tuong lai.

He thong can:

- Tao mot project record ro rang.
- Khong index file khong can thiet nhu dependencies, cache, build output, binary, secret files.
- Bao trang thai import/index de nguoi dung biet da xong hay loi.
- Xu ly project trung lap theo cach de hieu, khong tao nhieu card giong nhau ma khong giai thich.

Tieu chi dat:

- User them duoc project mau va thay project xuat hien trong tab Projects.
- Neu import loi, user biet ly do o muc co the hanh dong.
- Khong doc hoac hien thi secret/config nhay cam.

### Flow 2: Quan ly danh sach project

Nguoi dung can xem va quan ly cac project da import.

Chuc nang can co:

- Xem danh sach project.
- Xem ten project, nguon import ngan gon, trang thai index, tech stack, va thong tin tong quan can thiet.
- Mo workspace cua project.
- Re-index project.
- Xoa project.
- Tim kiem/loc project khi danh sach dai.

Thong tin tren project card phai uu tien phuc vu user:

- Ten project.
- Nguon import de hieu, khong hien path dai gay roi.
- Trang thai index.
- Tech stack duoc suy ra tu source code.
- So file da index.
- So API routes neu co backend.
- So function/class neu co gia tri cho viec hieu code.
- Thoi diem index gan nhat.

Khong nen hien thi mac dinh:

- Duong dan storage noi bo.
- Graph nodes neu user khong hieu no dung de lam gi.
- Chunks neu user khong can biet chi tiet retrieval.
- Con so "health" neu chua co cong thuc ro rang.

Tieu chi dat:

- User nhin card va hieu project la gi trong vai giay.
- Cac action phu nam trong menu ro rang.
- Delete khong xau, khong gay bam nham, va co xac nhan phu hop.

### Flow 3: Index va re-index codebase

Indexing bien source code thanh du lieu co the search, chat, graph, va citation.

Chuc nang can co:

- Scan file hop le.
- Parse code thanh file, symbol, endpoint, import, call, chunk.
- Luu ket qua vao database.
- Luu lich su indexing job.
- Re-index sach khi source code thay doi.
- Bao loi neu parser gap file khong ho tro ma khong lam hong ca job.

Tieu chi dat:

- Re-index nhieu lan khong tao du lieu rac hoac duplicate.
- Job status phan anh dung: indexing, indexed, failed.
- Neu mot file loi parse, cac file khac van co the duoc index khi hop ly.
- Ket qua search/chat dung voi lan index moi nhat.

### Flow 4: Hieu tong quan codebase

Sau khi index, user can co mot workspace de hieu project.

Chuc nang can co:

- Tong quan project.
- Danh sach file quan trong.
- Danh sach function/class quan trong.
- Danh sach endpoint neu co.
- Tech stack va framework duoc suy ra tu source code.
- Cac module hoac folder chinh.
- Goi y diem bat dau doc code.

Tieu chi dat:

- User moi co the biet project lam gi ma khong doc toan bo source.
- Thong tin hien thi dung ngon ngu user hieu, khong day thuat ngu noi bo.
- Neu thong tin la suy luan, he thong can the hien muc do chac chan hoac bang chung.

### Flow 5: Tim kiem trong codebase

User can tim nhanh thong tin trong source code.

Chuc nang can co:

- Search theo text.
- Search theo file path.
- Search theo function/class.
- Search theo endpoint.
- Search theo dependency hoac import trong tuong lai.
- Ket qua search co file, line, loai ket qua, va snippet.

Tieu chi dat:

- Search tra ve ket qua lien quan trong thoi gian ngan.
- User co the bam vao ket qua de xem ngu canh.
- Ket qua khong chi la text match, ma nen uu tien symbol/endpoint quan trong khi co the.

### Flow 6: Chat voi codebase

Assistant can tra loi cau hoi dua tren source code da index.

Chuc nang can co:

- Dat cau hoi tu nhien ve project.
- Lay evidence lien quan tu source code.
- Tra loi ngan gon, co cau truc.
- Kem citation den file/line/snippet.
- Tu choi hoac noi khong chac neu khong co bang chung.
- Goi y cau hoi tiep theo khi phu hop.

Tieu chi dat:

- Moi cau tra loi ve code phai co evidence.
- Khong duoc noi nhu chac chan neu retrieval khong tim thay bang chung.
- User co the mo evidence de kiem tra.

### Flow 7: Hieu API va runtime flow

Voi project backend, user can hieu API surface va flow xu ly request.

Chuc nang can co:

- Liet ke endpoints.
- Hien method, route, handler, file, line.
- Noi endpoint voi function/service/model lien quan khi co the.
- Cho phep hoi "endpoint nay lam gi" hoac "request nay di qua nhung file nao".

Tieu chi dat:

- User tim duoc endpoint quan trong ma khong can grep source.
- Assistant dua ra bang chung tu route va handler.
- Neu graph chua du thong tin, UI khong duoc gia vo la da trace day du.

### Flow 8: Dependency graph va impact analysis

Day la tinh nang can cho ban manh hon cua san pham, nhung nen co huong ro tu dau.

Chuc nang can co:

- Bieu dien quan he file, symbol, import, call, endpoint.
- Xem mot file/symbol duoc dung o dau.
- Du doan phan nao bi anh huong khi sua code.
- Ho tro assistant tra loi cau hoi ve dependency.

Tieu chi dat:

- Graph relation phai co nguon du lieu ro rang.
- Impact analysis phai noi ro "co bang chung" hay "suy luan".
- Khong hien thi graph phuc tap neu user khong rut ra duoc hanh dong.

### Flow 9: Settings va bao mat

User can cau hinh he thong ma khong lam lo secret.

Chuc nang can co:

- Cau hinh provider cho LLM/embedding khi tinh nang nay duoc them.
- Cau hinh ignore patterns.
- Cau hinh storage path neu can.
- Khong doc, index, log, hoac hien thi secret files.
- Khong commit credential.

Tieu chi dat:

- Secret files bi bo qua mac dinh.
- Neu can token, user nhap qua co che config an toan.
- Docs va logs khong chua secret.

### Flow 10: Agentic AI investigation

Day la nhom tinh nang lam AI Codebase Assistant khac voi chatbot RAG thong thuong. Assistant khong chi retrieve mot lan roi tra loi, ma co the lap ke hoach, goi nhieu tool, kiem tra evidence, va dieu chinh cau tra loi dua tren ngu canh.

Chuc nang can co:

- Phan loai intent cau hoi: API, file, symbol, dependency, impact, architecture, onboarding, debugging, refactor.
- Lap ke hoach kham pha codebase truoc khi tra loi.
- Chon tool phu hop: search, endpoint lookup, file detail, symbol detail, graph traversal, impact analysis, tests lookup, evidence viewer.
- Ket hop nhieu loai evidence: text chunks, symbols, endpoints, imports, calls, README/docs, graph relations.
- Kiem tra cau tra loi co du evidence truoc khi hien cho user.
- Noi ro khi chi co suy luan va khong du bang chung.
- Ho tro che do giai thich theo muc nguoi dung: beginner, developer, reviewer.

Tieu chi dat:

- Assistant co the xu ly cau hoi nhieu buoc nhu "authentication flow hoat dong nhu the nao?" hoac "neu sua User model thi anh huong dau?".
- Moi buoc quan trong trong cau tra loi co evidence hoac ly do ro rang.
- Assistant khong duoc goi LLM de doan thay cho viec truy xuat evidence tu index/graph.
- Neu evidence thieu, assistant phai hoi lai, tim them, hoac noi ro gioi han thay vi bia.

### Flow 11: Kiem thu va demo

San pham can co the demo lap lai.

Chuc nang can co:

- Bo project mau nho de test parser/index/search/chat.
- Backend tests cho import, index, re-index, delete, search, chat.
- Frontend lint/build.
- Demo checklist cho user tu tay thu.
- Sau moi thay doi lon, docs phai cap nhat theo code.

Tieu chi dat:

- Mot nguoi khac co the chay demo theo checklist ma khong can hoi tac gia.
- Test pass truoc khi commit cac thay doi quan trong.
- Neu tinh nang chua xong, UI/docs phai noi dung trang thai that.

## 4. Use Case Specification

Phan nay mo ta use case cho toan bo san pham, khong chi dung lai o baseline. Mot so use case co the duoc trien khai theo tung phase, nhung van duoc ghi lai de AI/Codex va developer hieu day du quy trinh san pham.

### 4.1 Use Case Coverage Map

| Nhom | Use case | Muc dich |
| --- | --- | --- |
| Project Onboarding | U001, U002, U003, U004, U005 | Dua source vao he thong, preview, tranh trung lap, import GitHub |
| Indexing Lifecycle | U006, U007, U008, U009 | Theo doi, re-index, xem job history, phat hien stale index |
| Codebase Understanding | U010, U011, U012, U013 | Workspace, file detail, symbol detail, diem bat dau doc code |
| Search and Evidence | U014, U015 | Search co filter va quan ly evidence/citation |
| Chat Assistant | U016, U017, U018 | Chat global, chat theo context, xu ly khi thieu evidence hoac citation cu |
| Agentic AI Layer | U032, U033, U034, U035, U036 | Planner agent, tool orchestration, evidence verification, multi-step investigation, explanation mode |
| API Understanding | U019, U020 | Xem endpoint va trace request flow |
| Graph and Impact | U021, U022, U023 | Dependency graph, impact analysis, related tests |
| Security and Settings | U024, U025, U026 | Ignore patterns, secret scanning, LLM/embedding provider |
| Data Management | U027, U028 | Storage, delete project |
| Demo and Evaluation | U029, U030 | Sample project, demo checklist, danh gia cau tra loi |
| Optional Multi-user | U031 | Dang nhap va phan quyen project neu san pham mo rong |

---

### U001 - Import project bang browser folder hoac ZIP

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U001 |
| Use Case | Import project bang browser folder hoac ZIP |
| Brief Description | Cho phep nguoi dung dua mot codebase co san vao AI Codebase Assistant de he thong tao repository record va chuan bi cho qua trinh preview/index. |
| Actor | Developer, reviewer, hoac nguoi demo dang co project can phan tich. |
| Pre-Condition | User da authenticated, frontend/backend san sang, upload nam trong enforced quota va source duoc gui qua browser folder/ZIP contract. Backend khong nhan host-local path tu user. |
| Result | He thong chi tao import session sau khi upload hoan tat va boundary checks pass, sau do chuyen den preview. Repository/source snapshot chi duoc tao khi confirm idempotently. |
| Main Scenario | Buoc 1: Nguoi dung mo tab Projects.<br><br>Buoc 2: Nguoi dung bam New Project.<br><br>Buoc 3: Nguoi dung chon upload folder, upload zip<br><br>Buoc 4: He thong validate source va doc metadata co ban.<br><br>Buoc 5: He thong tao import session va chuyen sang buoc preview truoc khi index. |
| Alternative Scenarios | Production v1 khong bo qua preview. ZIP duoc stream/extract trong isolated staging theo quota va cleanup contract. |
| Exception Flows | **Source khong ton tai hoac khong doc duoc:** Thong bao loi ro de user chon lai.<br><br>**Zip khong hop le:** Tu choi import va khong tao repository record hoan chinh.<br><br>**Source qua lon:** Canh bao va de nghi bo qua thu muc lon. |
| Non-Functional Constraints | Khong doc noi dung secret files. Khong log path noi bo qua dai neu khong can thiet. Import project nho phai co phan hoi trong vai giay. |

### U002 - Preview project truoc khi index

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U002 |
| Use Case | Preview project truoc khi index |
| Brief Description | Cho nguoi dung xem he thong sap index nhung gi truoc khi thuc su tao du lieu index. |
| Actor | Developer, nguoi demo, hoac reviewer muon kiem tra do an toan va pham vi index. |
| Pre-Condition | User da chon source hop le trong flow import. He thong co the scan metadata co ban. |
| Result | User nhin thay tong quan project, file se index, file bi skip, canh bao bao mat, ngon ngu/framework phat hien, va co the xac nhan Index. |
| Main Scenario | Buoc 1: He thong scan nhanh cau truc thu muc.<br><br>Buoc 2: He thong hien ten project, source label, kich thuoc, so file, ngon ngu chinh, framework nghi ngo, va ignore patterns dang ap dung.<br><br>Buoc 3: He thong hien danh sach file/folder se bi bo qua nhu `.git`, `node_modules`, `venv`, `dist`, `build`, binary, cache, secret-like files.<br><br>Buoc 4: User xem canh bao neu co.<br><br>Buoc 5: User bam Start Index de tao repository record chinh thuc va indexing job. |
| Alternative Scenarios | User chinh sua ignore patterns truoc khi index.<br><br>User huy import: he thong xoa import session tam va khong luu du lieu project. |
| Exception Flows | **Preview scan bi loi:** UI hien loi va cho phep thu lai.<br><br>**Khong co file hop le:** Khong cho index va giai thich ly do.<br><br>**Phat hien file co kha nang secret:** Hien canh bao, mac dinh skip file do. |
| Non-Functional Constraints | Preview khong duoc ton thoi gian qua lau. Khong hien noi dung secret trong preview. Cac con so uoc luong phai noi ro la estimate neu chua index that. |

### U003 - Phat hien va xu ly project trung lap

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U003 |
| Use Case | Phat hien va xu ly project trung lap |
| Brief Description | Tranh viec import cung mot project nhieu lan tao ra nhieu card giong nhau ma user khong hieu. |
| Actor | Developer hoac nguoi demo thu import nhieu lan. |
| Pre-Condition | He thong da co it nhat mot project truoc do hoac co the tinh duplicate signals tu source moi. |
| Result | User duoc thong bao neu project co kha nang trung lap va chon cach xu ly phu hop. |
| Main Scenario | Buoc 1: User import mot source moi.<br><br>Buoc 2: He thong so sanh ten project, source path, zip hash, GitHub URL, branch, commit, va cau truc file neu co.<br><br>Buoc 3: Neu phat hien trung lap, UI hien dialog giai thich.<br><br>Buoc 4: User chon Open existing, Re-index existing, Import as new copy, hoac Cancel.<br><br>Buoc 5: He thong thuc hien action duoc chon. |
| Alternative Scenarios | Neu chi nghi ngo trung lap thap, he thong co the chi hien warning nho trong preview. |
| Exception Flows | **Khong tinh duoc hash/source signal:** He thong van cho import nhung khong khang dinh khong trung lap.<br><br>**User chon re-index existing nhung source cu khong con:** He thong thong bao va de nghi import as new copy. |
| Non-Functional Constraints | Duplicate detection khong duoc lam cham dang ke flow import. UI phai giai thich bang ngon ngu de hieu, khong chi hien hash/path noi bo. |

### U004 - Import public GitHub repository

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U004 |
| Use Case | Import GitHub repository |
| Brief Description | Cho phep nguoi dung import public GitHub repository qua profile URL/host bi gioi han. Private Git va arbitrary host nam ngoai production v1. |
| Actor | Developer, reviewer, hoac tech lead co repository tren GitHub. |
| Pre-Condition | User co GitHub URL public hop le theo parser/allowlist production v1. |
| Result | He thong lay source tu GitHub, ghi nhan repo metadata, branch/commit, va dua project vao flow preview/index. |
| Main Scenario | Buoc 1: User chon Import GitHub Repository.<br><br>Buoc 2: User nhap GitHub URL va branch neu can.<br><br>Buoc 3: He thong validate URL va kiem tra quyen truy cap.<br><br>Buoc 4: He thong clone/download source vao storage duoc quan ly.<br><br>Buoc 5: He thong hien preview voi repo name, branch, commit, file count, languages, ignored files.<br><br>Buoc 6: User xac nhan index. |
| Alternative Scenarios | User chon branch/tag public khac. Private repo can requirement, threat model, ADR va task rieng. |
| Exception Flows | **URL khong hop le:** Tu choi va huong dan dinh dang dung.<br><br>**Khong co quyen truy cap:** Bao loi authentication/authorization ro rang.<br><br>**Clone/download failed:** Giu UI trong import flow va cho phep retry. |
| Non-Functional Constraints | Chi HTTPS GitHub profile duoc phep; chan credential trong URL, redirect/SSRF, hooks, submodules, LFS va clone khong gioi han. Repo metadata luu branch/commit va snapshot hash. |

### U005 - Sync source moi tu GitHub

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U005 |
| Use Case | Sync source moi tu GitHub |
| Brief Description | Cho phep project da import tu GitHub cap nhat source moi va re-index theo commit moi. |
| Actor | Developer dang theo doi codebase thay doi theo thoi gian. |
| Pre-Condition | Project co source la GitHub repository va con thong tin remote URL, branch, commit cu. |
| Result | He thong lay commit moi, cap nhat source, danh dau index stale hoac tao re-index job. |
| Main Scenario | Buoc 1: User mo project GitHub trong Projects hoac Workspace.<br><br>Buoc 2: User bam Sync latest.<br><br>Buoc 3: He thong kiem tra commit moi tren branch dang theo doi.<br><br>Buoc 4: Neu co thay doi, he thong cap nhat source va hien tom tat changed files neu co the.<br><br>Buoc 5: User xac nhan re-index.<br><br>Buoc 6: He thong tao indexing job moi. |
| Alternative Scenarios | Neu khong co commit moi, UI thong bao project dang moi nhat.<br><br>User chon sync nhung chua re-index ngay, project duoc danh dau stale. |
| Exception Flows | **Mat quyen truy cap repo:** Thong bao loi va giu source/index cu.<br><br>**Conflict storage:** He thong khong ghi de source cu neu update that bai giua chung. |
| Non-Functional Constraints | Sync phai giu duoc commit/index version de citation cu khong bi hieu nham. |

### U006 - Theo doi tien trinh indexing

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U006 |
| Use Case | Theo doi tien trinh indexing |
| Brief Description | Cho nguoi dung biet he thong dang lam gi trong qua trinh indexing va neu loi thi loi o dau. |
| Actor | Developer hoac nguoi demo vua import/re-index project. |
| Pre-Condition | Da co indexing job duoc tao cho mot project. |
| Result | User thay job/attempt, server-declared stage, progress unit, candidate index version, warning/error diagnostics va prior active-version preservation. Job state va capability state khong bi gop. |
| Main Scenario | Buoc 1: Sau khi user bam Start Index, UI chuyen sang Indexing Status.<br><br>Buoc 2: He thong hien stage hien tai, progress, elapsed time, file processed, file skipped, warnings, errors.<br><br>Buoc 3: User co the quay lai Projects; project card van hien status dang indexing.<br><br>Buoc 4: Khi job xong, UI cap nhat sang indexed hoac completed with warnings.<br><br>Buoc 5: User bam Open Workspace de xem ket qua. |
| Alternative Scenarios | Neu indexing chay background, UI poll hoac subscribe status.<br><br>Neu project nho va index nhanh, UI co the hien completed gan nhu ngay. |
| Exception Flows | **Job failed:** Hien stage that bai, reason, file lien quan neu co, va action retry/re-index.<br><br>**Connection UI mat:** Khi user quay lai, UI doc job status moi nhat tu backend. |
| Non-Functional Constraints | Status khong duoc bao thanh cong truoc activation transaction. File/profile failure tuan theo capability-scoped validation contract; UI khong tu hard-code pipeline Python. |

### U007 - Re-index project

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U007 |
| Use Case | Re-index project |
| Brief Description | Cap nhat lai index khi source thay doi, parser duoc cai thien, hoac user muon lam sach ket qua cu. |
| Actor | Developer dang bao tri project hoac nguoi demo can reset du lieu. |
| Pre-Condition | Project da ton tai. Source con doc duoc hoac co ban copy trong storage duoc quan ly. |
| Result | Search, workspace, API view, graph, chat su dung index version moi nhat. |
| Main Scenario | Buoc 1: User chon Re-index tu project card hoac workspace.<br><br>Buoc 2: He thong kiem tra job hien tai va source availability.<br><br>Buoc 3: He thong tao indexing job moi va chuyen status sang indexing.<br><br>Buoc 4: He thong build index moi theo co che an toan, tranh de du lieu nua cu nua moi.<br><br>Buoc 5: Khi thanh cong, he thong active index version moi va cap nhat UI. |
| Alternative Scenarios | Neu job cu dang chay, he thong chan re-index moi hoac dua vao queue theo chinh sach san pham.<br><br>Neu re-index chi can parser/index metadata, co the khong can copy source lai. |
| Exception Flows | **Source bi xoa:** Job failed va UI giai thich can import lai hoac sync lai.<br><br>**Database write failed:** Khong active index moi, giu index cu neu con an toan.<br><br>**Parser loi mot so file:** Completed with warnings neu phan con lai van dung duoc. |
| Non-Functional Constraints | Re-index phai idempotent o muc user: chay nhieu lan khong tao duplicate records. Can co index_version de chat/citation biet du lieu thuoc lan index nao. |

### U008 - Xem indexing job history va parser warnings

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U008 |
| Use Case | Xem indexing job history va parser warnings |
| Brief Description | Cho nguoi dung xem lich su cac lan index, ket qua, loi, warning, skipped files de hieu do tin cay cua du lieu. |
| Actor | Developer, reviewer, hoac nguoi demo can debug tai sao search/chat thieu ket qua. |
| Pre-Condition | Project da co it nhat mot indexing job. |
| Result | User thay duoc timeline index va chi tiet tung job: status, thoi gian, file indexed, skipped, warnings, errors. |
| Main Scenario | Buoc 1: User mo Indexing History trong workspace.<br><br>Buoc 2: He thong hien danh sach job theo thoi gian.<br><br>Buoc 3: User chon mot job de xem chi tiet.<br><br>Buoc 4: UI hien stage summary, parser warnings, skipped files va ly do skip.<br><br>Buoc 5: User co the retry/re-index neu can. |
| Alternative Scenarios | Neu khong co warning, UI hien trang thai clean.<br><br>Neu job qua cu, UI chi hien summary va luu log chi tiet theo retention policy. |
| Exception Flows | **Khong tai duoc logs:** UI hien summary neu co va cho retry.<br><br>**File warning khong con ton tai:** UI thong bao warning thuoc index version cu. |
| Non-Functional Constraints | Logs khong duoc chua secret content. Warning phai co file path, reason, va stage neu co. |

### U009 - Phat hien index da cu so voi source

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U009 |
| Use Case | Phat hien index da cu so voi source |
| Brief Description | Canh bao user khi source code co the da thay doi sau lan index gan nhat. |
| Actor | Developer dang bao tri project. |
| Pre-Condition | He thong co last_indexed_at, index_version, va metadata source nhu modified time, file hash, hoac Git commit. |
| Result | UI hien trang thai Index may be outdated va goi y re-index khi can. |
| Main Scenario | Buoc 1: User mo Projects hoac Workspace.<br><br>Buoc 2: He thong so sanh source metadata voi lan index gan nhat.<br><br>Buoc 3: Neu source thay doi, he thong danh dau project stale.<br><br>Buoc 4: UI hien canh bao va nut Re-index.<br><br>Buoc 5: User re-index de cap nhat ket qua. |
| Alternative Scenarios | Voi GitHub project, he thong so sanh indexed commit voi remote commit.<br><br>Voi local project, he thong so sanh modified time/hash neu co quyen doc. |
| Exception Flows | **Khong kiem tra duoc source:** UI noi ro khong xac minh duoc do moi cua index.<br><br>**Source bi xoa:** Project chuyen sang trang thai source missing thay vi stale thong thuong. |
| Non-Functional Constraints | Khong khang dinh index cu neu chi co signal yeu. Nen phan biet `fresh`, `possibly stale`, `stale`, va `source missing`. |

### U010 - Xem workspace tong quan codebase

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U010 |
| Use Case | Xem workspace tong quan codebase |
| Brief Description | Cho nguoi dung mo mot project va hieu nhanh codebase thong qua overview co bang chung. |
| Actor | Developer moi, tech lead, reviewer, hoac nguoi demo. |
| Pre-Condition | Project da duoc index thanh cong hoac completed with warnings. |
| Result | Workspace hien tech stack, modules/folders chinh, file quan trong, symbols quan trong, endpoints, graph summary, va suggested reading path. |
| Main Scenario | Buoc 1: User bam Open Workspace.<br><br>Buoc 2: He thong tai repository summary va index summary.<br><br>Buoc 3: Overview hien ngon ngu/framework, entry points, important files, endpoints, symbols, va warning neu index chua day du.<br><br>Buoc 4: User bam vao file/symbol/endpoint/evidence de xem chi tiet.<br><br>Buoc 5: User co the chuyen sang Files, Search, API, Graph, Chat, Settings. |
| Alternative Scenarios | Project chua co endpoint: API section hien empty state.<br><br>Project co warning: Overview hien badge completed with warnings va link den U008. |
| Exception Flows | **Workspace data loi:** UI hien retry va khong dieu huong user ra khoi context project.<br><br>**Index thieu:** UI hien phan co du lieu va noi ro phan nao chua co. |
| Non-Functional Constraints | Workspace phai uu tien thong tin user hieu duoc. Tranh hien chunks, graph nodes, raw IDs neu khong co giai thich. |

### U011 - Xem file explorer va file detail

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U011 |
| Use Case | Xem file explorer va file detail |
| Brief Description | Cho nguoi dung duyet cau truc thu muc, mo file, va xem metadata/symbols lien quan. |
| Actor | Developer can doc code co dinh huong. |
| Pre-Condition | Project da duoc index va co records cho files. |
| Result | User xem duoc cay thu muc, danh sach file, file metadata, snippet/source preview neu duoc phep, imports, symbols, endpoints lien quan. |
| Main Scenario | Buoc 1: User mo Files view trong workspace.<br><br>Buoc 2: He thong hien tree hoac danh sach folder/file.<br><br>Buoc 3: User chon mot file.<br><br>Buoc 4: UI hien language, size, line count, indexed status, symbols, imports, related endpoints, related tests neu co.<br><br>Buoc 5: User co the hoi assistant ve file nay. |
| Alternative Scenarios | File qua lon: UI hien metadata va snippet gioi han.<br><br>File bi skip: UI hien ly do skip thay vi noi dung. |
| Exception Flows | **File source khong doc duoc:** UI hien metadata/indexed snippet neu co va bao loi context.<br><br>**Line number khong co:** UI khong tao line gia, chi hien file/snippet. |
| Non-Functional Constraints | Khong hien noi dung secret/binary/dependency files da skip. File tree phai de doc voi project vua va lon. |

### U012 - Xem symbol detail

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U012 |
| Use Case | Xem symbol detail |
| Brief Description | Cho user xem chi tiet function, class, method, component, hoac symbol quan trong trong codebase. |
| Actor | Developer moi, developer bao tri, reviewer. |
| Pre-Condition | Parser da extract symbols va line ranges neu co. |
| Result | User thay symbol name, type, signature, file, line, docstring/comment, calls, called by, related endpoints/tests neu co. |
| Main Scenario | Buoc 1: User bam vao symbol trong Search, File detail, Workspace, hoac Graph.<br><br>Buoc 2: He thong tai symbol record va relations lien quan.<br><br>Buoc 3: UI hien signature, file/line, snippet, documentation, imports/calls/called by.<br><br>Buoc 4: User co the bam Ask about this symbol hoac Analyze impact. |
| Alternative Scenarios | Symbol chi duoc extract mot phan: UI hien phan co bang chung va ghi ro limitation.<br><br>Symbol la frontend component: UI hien file, props neu parser ho tro, va import/export relations. |
| Exception Flows | **Symbol khong con ton tai sau re-index:** UI thong bao stale va goi y search lai.<br><br>**Parser khong lay duoc signature:** UI hien ten va snippet thay vi doan thong tin gia. |
| Non-Functional Constraints | Moi thong tin ve relation phai co nguon du lieu ro rang: AST, import parser, call graph, endpoint extractor, hoac retrieval evidence. |

### U013 - Goi y diem bat dau doc code

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U013 |
| Use Case | Goi y diem bat dau doc code |
| Brief Description | De xuat cac file/module nen doc truoc de nguoi moi hieu codebase nhanh hon. |
| Actor | Developer moi tham gia project, reviewer, nguoi demo. |
| Pre-Condition | Project da co file metadata, symbols, endpoints, imports, framework signals. |
| Result | Workspace hien danh sach suggested reading path kem ly do va evidence. |
| Main Scenario | Buoc 1: User mo Workspace Overview.<br><br>Buoc 2: He thong xac dinh entry points, API routers, config files, models, services, high-degree files, README/docs neu co.<br><br>Buoc 3: UI hien 3-7 goi y doc code.<br><br>Buoc 4: Moi goi y co ly do: entry point, nhieu endpoints, duoc import nhieu, chua model/schema, hoac la module chinh.<br><br>Buoc 5: User bam vao goi y de mo file detail. |
| Alternative Scenarios | Project khong co framework ro: he thong dua goi y dua tren file tree va naming convention.<br><br>Project co README tot: README co the la goi y dau tien. |
| Exception Flows | **Khong du evidence:** UI noi ro chua du du lieu de goi y manh, va chi hien file co kha nang la entry point.<br><br>**Index warning nhieu:** UI canh bao reading path co the thieu. |
| Non-Functional Constraints | Khong duoc khang dinh tuyet doi. Nen dung ngon ngu nhu "nen bat dau tu" kem ly do. |

### U014 - Tim kiem trong codebase co filter

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U014 |
| Use Case | Tim kiem trong codebase co filter |
| Brief Description | Cho nguoi dung tim file, symbol, endpoint, dependency, hoac code snippet voi bo loc de giam nhieu. |
| Actor | Developer can dinh vi code nhanh. |
| Pre-Condition | Project da duoc index va co du lieu files, symbols, endpoints, chunks. |
| Result | He thong tra ve ket qua lien quan, co file path, line, result type, snippet, score neu can, va filters dang ap dung. |
| Main Scenario | Buoc 1: User mo Search view.<br><br>Buoc 2: User nhap query nhu ten function, class, route, file path, hoac cau hoi ngan.<br><br>Buoc 3: User chon filter: file, symbol, endpoint, chunk, language, folder/module, framework, test files.<br><br>Buoc 4: He thong search va rank ket qua.<br><br>Buoc 5: User bam result de mo file/symbol/endpoint detail. |
| Alternative Scenarios | User search global tu top bar, he thong tim trong project hien tai hoac tat ca project tuy context.<br><br>User search endpoint bang route `/api/users`. |
| Exception Flows | **Khong co ket qua:** Hien empty state va goi y query khac.<br><br>**Query qua ngan:** Yeu cau them ky tu hoac filter.<br><br>**Search service loi:** Hien retry. |
| Non-Functional Constraints | Search project nho/vua phai phan hoi nhanh. Ket qua phai uu tien symbol/endpoint quan trong, khong chi text match dai. |

### U015 - Xem evidence va citation detail

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U015 |
| Use Case | Xem evidence va citation detail |
| Brief Description | Cho user kiem tra bang chung ma search/chat/API/impact analysis dua ra. |
| Actor | Developer, reviewer, tech lead, nguoi cham diem. |
| Pre-Condition | He thong da luu evidence record hoac co file/snippet/line tu index. |
| Result | User mo duoc citation/evidence de xem file path, line range, snippet, source type, index version, va context xung quanh. |
| Main Scenario | Buoc 1: User bam citation trong cau tra loi chat hoac analysis.<br><br>Buoc 2: UI mo evidence drawer/detail.<br><br>Buoc 3: He thong hien file path, line range, snippet, symbol/endpoint lien quan, index version.<br><br>Buoc 4: User co the mo file detail hoac copy citation. |
| Alternative Scenarios | Evidence den tu graph relation: UI hien relation type va nguon parser.<br><br>Evidence den tu endpoint extractor: UI hien route decorator va handler. |
| Exception Flows | **Citation thuoc index cu:** UI hien warning stale citation.<br><br>**File khong con ton tai:** UI hien snippet da luu neu an toan va thong bao source thay doi. |
| Non-Functional Constraints | Citation phai kiem chung duoc. Khong hien snippet cua secret file. Khong tao line range gia neu parser khong co. |

### U016 - Chat voi codebase co evidence

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U016 |
| Use Case | Chat voi codebase co evidence |
| Brief Description | Cho phep user dat cau hoi tu nhien ve codebase va nhan cau tra loi dua tren evidence. |
| Actor | Developer moi, developer bao tri, reviewer, nguoi demo. |
| Pre-Condition | Project da duoc index. Retrieval, evidence store, va LLM/fallback da san sang. |
| Result | Assistant tra loi ngan gon, co cau truc, co citations. Neu thieu evidence, assistant noi ro gioi han. |
| Main Scenario | Buoc 1: User mo Chat trong workspace.<br><br>Buoc 2: User hoi vi du "API dang nhap nam o dau?" hoac "module indexing lam gi?".<br><br>Buoc 3: He thong retrieval files, symbols, endpoints, chunks, graph relations lien quan.<br><br>Buoc 4: Assistant tong hop cau tra loi dua tren evidence.<br><br>Buoc 5: UI hien answer va citations.<br><br>Buoc 6: User bam citation de kiem tra. |
| Alternative Scenarios | User hoi tiep dua tren cau tra loi truoc: assistant dung conversation context nhung van retrieval lai khi can evidence.<br><br>Neu LLM khong cau hinh, he thong co the dung fallback deterministic cho mot so cau hoi search/summarize don gian. |
| Exception Flows | **Khong co evidence:** Assistant khong ket luan chac chan va goi y hoi cu the hon.<br><br>**LLM provider loi:** Hien loi ro rang va khong bia cau tra loi.<br><br>**Index stale:** Assistant canh bao ket qua co the cu. |
| Non-Functional Constraints | Moi cau tra loi ve code phai co evidence. Phai phan biet ro giua bang chung va suy luan. |

### U017 - Chat theo context hien tai

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U017 |
| Use Case | Chat theo context hien tai |
| Brief Description | Cho user hoi assistant ve file, symbol, endpoint, search result, hoac evidence dang duoc chon. |
| Actor | Developer dang doc code trong workspace. |
| Pre-Condition | User dang o file detail, symbol detail, endpoint detail, graph node, hoac da chon evidence. |
| Result | Assistant tra loi dua tren context hien tai va retrieval bo sung, giam viec hoi qua rong. |
| Main Scenario | Buoc 1: User mo mot file/symbol/endpoint.<br><br>Buoc 2: User bam Ask about this hoac nhap cau hoi trong chat panel co context.<br><br>Buoc 3: He thong dua context ID vao retrieval.<br><br>Buoc 4: Assistant tra loi ve doi tuong dang chon, kem citation.<br><br>Buoc 5: User co the tiep tuc hoi "no duoc dung o dau?" hoac "neu sua thi anh huong gi?". |
| Alternative Scenarios | User chon nhieu search results lam evidence truoc khi hoi.<br><br>User xoa context de quay lai chat global. |
| Exception Flows | **Context da stale sau re-index:** UI canh bao va de nghi refresh.<br><br>**Context khong co du evidence:** Assistant noi ro va hoi user co muon search rong hon khong. |
| Non-Functional Constraints | Context khong thay the evidence. Assistant van phai co citation khi noi ve source code. |

### U018 - Quan ly chat history va citation stale

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U018 |
| Use Case | Quan ly chat history va citation stale |
| Brief Description | Luu lich su hoi dap theo project va canh bao khi citations trong cau tra loi cu khong con khop index hien tai. |
| Actor | Developer quay lai lam viec voi project sau nhieu lan re-index. |
| Pre-Condition | He thong co chat sessions gan voi project va index_version. |
| Result | User xem lai chat history, biet cau tra loi nao thuoc index cu, va co the refresh answer neu can. |
| Main Scenario | Buoc 1: User mo Chat History trong project.<br><br>Buoc 2: He thong hien cac session/cau hoi cu.<br><br>Buoc 3: Neu answer thuoc index version cu, UI hien badge stale evidence.<br><br>Buoc 4: User bam Refresh answer de retrieval lai tren index moi.<br><br>Buoc 5: He thong tao cau tra loi moi va giu link voi cau tra loi cu neu can so sanh. |
| Alternative Scenarios | User xoa chat session cu.<br><br>Project da bi xoa thi chat history cung bi xoa theo chinh sach data. |
| Exception Flows | **Evidence file khong con ton tai:** UI thong bao citation cu khong the verify.<br><br>**Khong load duoc history:** Hien retry. |
| Non-Functional Constraints | Chat history khong duoc luu secret content. Citation phai gan index_version de tranh hieu nham. |

### U019 - Xem API endpoints va endpoint detail

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U019 |
| Use Case | Xem API endpoints va endpoint detail |
| Brief Description | Cho user xem API surface cua backend project va chi tiet tung endpoint. |
| Actor | Backend developer, frontend developer, reviewer, nguoi demo. |
| Pre-Condition | Project co backend framework duoc ho tro nhu FastAPI va endpoints da duoc extract. |
| Result | UI hien method, route, handler, file, line, request/response schema neu co, dependency/auth neu parser phat hien. |
| Main Scenario | Buoc 1: User mo API view.<br><br>Buoc 2: UI hien danh sach endpoints co filter theo method, route, file/module.<br><br>Buoc 3: User chon endpoint.<br><br>Buoc 4: UI hien handler, decorator/route snippet, file/line, related function/service/model neu co.<br><br>Buoc 5: User co the hoi assistant ve endpoint nay. |
| Alternative Scenarios | Project khong co endpoint: UI hien empty state co giai thich.<br><br>Parser chi extract route nhung chua trace service: UI chi hien phan co evidence. |
| Exception Flows | **Endpoint extraction thieu/sai:** UI khong khang dinh qua muc va cho re-index sau khi parser cai thien.<br><br>**File source khong doc duoc:** Endpoint item hien loi context thay vi crash. |
| Non-Functional Constraints | Do chinh xac quan trong hon so luong. Moi endpoint nen co file/line khi co the. |

### U020 - Trace request flow

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U020 |
| Use Case | Trace request flow |
| Brief Description | Giai thich request di qua route, handler, service, model/repository, response nhu the nao neu co du graph/evidence. |
| Actor | Developer can hieu runtime flow cua backend. |
| Pre-Condition | Endpoint da duoc extract va graph/call/import relations co du thong tin toi thieu. |
| Result | User thay chuoi xu ly request co evidence va limitation ro rang. |
| Main Scenario | Buoc 1: User chon mot endpoint hoac hoi "request nay di qua nhung file nao?".<br><br>Buoc 2: He thong lay endpoint handler va graph relations lien quan.<br><br>Buoc 3: He thong tao flow dang Route -> Handler -> Service -> Model/Repository -> Response neu co du du lieu.<br><br>Buoc 4: UI hien moi buoc kem file/line/evidence.<br><br>Buoc 5: Neu co buoc suy luan, UI gan nhan inferred. |
| Alternative Scenarios | Graph khong du: UI hien partial trace va noi ro chua trace day du.<br><br>Project frontend-only: use case khong ap dung va API view empty. |
| Exception Flows | **Call graph sai/thieu:** Assistant khong duoc noi nhu chac chan.<br><br>**Cycle hoac flow phuc tap:** UI tom tat va cho mo chi tiet. |
| Non-Functional Constraints | Phai phan biet evidence-based va inferred. Khong tao runtime flow gia neu chi co text match. |

### U021 - Xem dependency graph thuc dung

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U021 |
| Use Case | Xem dependency graph thuc dung |
| Brief Description | Cho user xem quan he file, symbol, import, call, endpoint theo cach co the hanh dong, khong chi la do thi phuc tap. |
| Actor | Developer bao tri, reviewer, tech lead. |
| Pre-Condition | Index co graph relations nhu imports, defines, calls, endpoint_handler. |
| Result | User biet file/symbol nay depends on ai, used by ai, calls ai, called by ai, related endpoints/tests nao. |
| Main Scenario | Buoc 1: User mo Graph view hoac bam Related trong file/symbol detail.<br><br>Buoc 2: He thong hien node trung tam va cac nhom relation: Depends on, Used by, Calls, Called by, Related endpoints, Related tests.<br><br>Buoc 3: User loc relation type hoac depth.<br><br>Buoc 4: User bam relation de mo evidence va object detail.<br><br>Buoc 5: User co the hoi assistant ve dependency nay. |
| Alternative Scenarios | UI co the hien graph visualization hoac danh sach grouped relations tuy phase.<br><br>Graph qua lon: mac dinh chi hien 1-hop relations. |
| Exception Flows | **Relation khong chac chan:** Gan nhan inferred/low confidence.<br><br>**Graph data thieu:** UI hien partial graph va link den parser warnings. |
| Non-Functional Constraints | Graph phai co nguon du lieu ro rang. Khong hien node count thuan tuy neu user khong rut ra hanh dong. |

### U022 - Impact analysis khi sua file hoac symbol

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U022 |
| Use Case | Impact analysis khi sua file hoac symbol |
| Brief Description | Du doan va giai thich nhung phan code co the bi anh huong khi user sua mot file, function, class, model, hoac endpoint. |
| Actor | Developer dang bao tri code, reviewer danh gia rui ro thay doi. |
| Pre-Condition | Co graph relations, file/symbol metadata, endpoint links, va related tests neu co. |
| Result | User nhin thay direct impact, possible impact, related endpoints, related tests, va evidence cho tung nhan dinh. |
| Main Scenario | Buoc 1: User chon file/symbol va bam Analyze Impact.<br><br>Buoc 2: He thong lay callers, imports, called functions, endpoints, tests, model/schema relations.<br><br>Buoc 3: He thong chia ket qua thanh Evidence-based impact va Inferred impact.<br><br>Buoc 4: UI hien muc do rui ro, danh sach file/symbol/endpoints co the anh huong, va evidence.<br><br>Buoc 5: User co the mo tung item hoac hoi assistant tiep. |
| Alternative Scenarios | Neu graph chua du, he thong chi hien direct dependencies va noi ro limitation.<br><br>User chon endpoint thi he thong phan tich handler/service/model lien quan. |
| Exception Flows | **Khong co relation:** He thong noi khong du evidence, khong khang dinh khong co anh huong.<br><br>**Index stale:** Canh bao re-index truoc khi phan tich. |
| Non-Functional Constraints | Impact analysis khong duoc gia vo la static analysis hoan hao. Moi ket luan nen co evidence hoac nhan la suy luan. |

### U023 - Tim tests lien quan den code duoc chon

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U023 |
| Use Case | Tim tests lien quan den code duoc chon |
| Brief Description | Goi y cac test files/test cases nen chay khi user sua mot file, symbol, endpoint, hoac module. |
| Actor | Developer dang sua code va muon kiem tra nhanh. |
| Pre-Condition | Project co test files hoac naming convention test duoc phat hien. |
| Result | User thay danh sach related tests va ly do lien quan. |
| Main Scenario | Buoc 1: User chon file/symbol/endpoint.<br><br>Buoc 2: User bam Find related tests.<br><br>Buoc 3: He thong tim tests dua tren import/call graph, naming convention, folder structure, va text references.<br><br>Buoc 4: UI hien test files, test functions neu co, command goi y neu phat hien framework.<br><br>Buoc 5: User mo test detail hoac copy command. |
| Alternative Scenarios | Neu khong tim thay test, UI noi ro khong co evidence ve test lien quan.<br><br>Neu project khong co test folder, UI giai thich va co the goi y them test. |
| Exception Flows | **Test parser chua ho tro:** UI chi hien file-level candidates.<br><br>**Command test khong chac:** Gan nhan suggested/inferred. |
| Non-Functional Constraints | Khong duoc khang dinh test coverage day du neu chi dua tren heuristic. |

### U024 - Cau hinh ignore patterns

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U024 |
| Use Case | Cau hinh ignore patterns |
| Brief Description | Cho user xem va chinh sua quy tac bo qua file/folder truoc khi index hoac re-index. |
| Actor | Developer muon kiem soat pham vi indexing. |
| Pre-Condition | User dang o Preview, Project Settings, hoac Re-index settings. |
| Result | He thong ap dung ignore patterns khi scan/index va ghi lai skipped files. |
| Main Scenario | Buoc 1: User mo Ignore Settings.<br><br>Buoc 2: UI hien patterns mac dinh nhu `.git/`, `node_modules/`, `.venv/`, `dist/`, `build/`, `__pycache__/`, binary, cache, secret-like files.<br><br>Buoc 3: User them/sua/xoa pattern.<br><br>Buoc 4: He thong validate pattern va canh bao neu qua rong.<br><br>Buoc 5: User save va ap dung trong lan index/re-index tiep theo. |
| Alternative Scenarios | User reset ve default ignore rules.<br><br>User apply pattern rieng cho mot project. |
| Exception Flows | **Pattern sai cu phap:** UI bao loi va khong save.<br><br>**Pattern bo qua gan het project:** UI canh bao manh truoc khi cho save. |
| Non-Functional Constraints | Ignore rules phai uu tien an toan. Cac default patterns khong nen de user vo tinh index dependencies/secret. |

### U025 - Secret scanning va canh bao bao mat

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U025 |
| Use Case | Secret scanning va canh bao bao mat |
| Brief Description | Phat hien va bo qua cac file/noi dung co kha nang chua credential, token, private key, hoac secret. |
| Actor | Developer, reviewer, nguoi demo quan tam an toan du lieu. |
| Pre-Condition | He thong dang preview, scan, index, search, hoac hien file detail. |
| Result | Secret-like files/noi dung khong bi index, khong hien snippet, khong log noi dung; UI hien canh bao an toan co hanh dong duoc. |
| Main Scenario | Buoc 1: He thong scan file path/name/type va mot so pattern an toan neu duoc phep.<br><br>Buoc 2: He thong phat hien `.env`, `*.pem`, `*.key`, `id_rsa`, `credentials.json`, `secrets.*`, hoac noi dung nghi ngo API key.<br><br>Buoc 3: He thong skip file/noi dung do khoi index.<br><br>Buoc 4: UI hien warning "Skipped possible secret" ma khong hien noi dung secret.<br><br>Buoc 5: Log chi ghi reason va path rut gon neu an toan. |
| Alternative Scenarios | User them pattern secret rieng.<br><br>Admin/developer co the cau hinh strict mode. |
| Exception Flows | **False positive:** User co the override chi khi co xac nhan ro va he thong ghi lai choice.<br><br>**Secret phat hien sau khi da index:** He thong xoa index lien quan va canh bao re-index. |
| Non-Functional Constraints | Bao mat uu tien hon coverage. Khong bao gio echo secret ra UI/log/chat/citation. |

### U026 - Cau hinh LLM va embedding provider

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U026 |
| Use Case | Cau hinh LLM va embedding provider |
| Brief Description | Cho user cau hinh provider/model dung cho chat, embedding, retrieval, hoac fallback. |
| Actor | Developer setup he thong, nguoi demo, hoac admin local app. |
| Pre-Condition | San pham co ho tro LLM/embedding provider. User co API key/token neu provider yeu cau. |
| Result | He thong co provider config hop le, test connection thanh cong, va dung config do cho indexing/chat. |
| Main Scenario | Buoc 1: User mo Settings -> AI Provider.<br><br>Buoc 2: User chon provider, chat model, embedding model.<br><br>Buoc 3: User nhap API key/token qua input an toan.<br><br>Buoc 4: User bam Test connection.<br><br>Buoc 5: He thong validate va save config theo co che an toan.<br><br>Buoc 6: Chat/indexing su dung config moi. |
| Alternative Scenarios | User chon local model/no-key provider neu ho tro.<br><br>User reset provider ve default/fallback. |
| Exception Flows | **Provider loi:** Hien message ro va khong mat config cu neu update that bai.<br><br>**Embedding model doi:** Canh bao user can re-index de embeddings dong bo. |
| Non-Functional Constraints | API key khong duoc log, khong hien lai full, khong commit vao docs. Provider error khong duoc lam assistant bia cau tra loi. |

### U027 - Quan ly storage va du lieu project

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U027 |
| Use Case | Quan ly storage va du lieu project |
| Brief Description | Cho user/developer hieu va quan ly dung luong source copy, index data, embeddings, graph data, va logs cua project. |
| Actor | Developer local app, nguoi demo can don dep du lieu, admin neu co. |
| Pre-Condition | Project da import va co du lieu duoc luu trong storage/database. |
| Result | User xem duoc storage summary va thuc hien cleanup an toan. |
| Main Scenario | Buoc 1: User mo Project Settings -> Storage.<br><br>Buoc 2: UI hien source storage, index records, embeddings, graph data, job logs, chat history size neu co.<br><br>Buoc 3: User chon action: clear index, rebuild index, delete source copy, delete project.<br><br>Buoc 4: He thong hien xac nhan cho action nguy hiem.<br><br>Buoc 5: Backend thuc hien cleanup trong pham vi project. |
| Alternative Scenarios | Source da duoc copy vao managed storage thi he thong chi xoa source copy thuoc manifest cua repository; source goc tren may nguoi dung hoac public Git remote khong nam trong pham vi xoa. |
| Exception Flows | **Xoa partial failed:** UI hien warning va ghi log don dep sau.<br><br>**Action anh huong chat/citation:** UI canh bao truoc. |
| Non-Functional Constraints | Khong duoc xoa ngoai pham vi storage duoc quan ly. Phai phan biet source goc va source copy. |

### U028 - Xoa project

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U028 |
| Use Case | Xoa project |
| Brief Description | Cho user xoa project khong can nua de lam sach danh sach Projects va du lieu index/storage/chat lien quan. |
| Actor | Nguoi demo, developer, reviewer. |
| Pre-Condition | Project ton tai trong he thong. |
| Result | Repository chuyen sang `deleting`, operation bat dong bo duoc tra ve, va chi chuyen `deleted` sau khi validator xac nhan cleanup hoan tat. UI khong cho khoi tao cong viec moi tren repository dang xoa. |
| Main Scenario | Buoc 1: User mo menu phu tren project card hoac Project Settings.<br><br>Buoc 2: User chon Delete.<br><br>Buoc 3: UI hien xac nhan, giai thich du lieu nao se bi xoa hoac giu theo retention policy.<br><br>Buoc 4: User xac nhan voi idempotency key.<br><br>Buoc 5: Backend tombstone repository, yeu cau cancel job, fence worker, doi lease ket thuc/het han, roi cleanup record va managed artifact theo manifest.<br><br>Buoc 6: UI theo doi deletion operation; chi hien success terminal khi repository la `deleted`. |
| Alternative Scenarios | User huy xac nhan thi khong xoa gi.<br><br>Lap lai cung request tra ve cung deletion operation; repository dang indexing van dung cung quy trinh tombstone-cancel-fence-drain-clean. |
| Exception Flows | **Project not found/khong thuoc principal:** Backend tra non-disclosing 404 va ghi audit an toan.<br><br>**Cleanup database hoac storage partial failed:** Repository giu `deleting`, UI hien remediation an toan va backend retry idempotently.<br><br>**User dang o workspace project bi xoa:** Dieu huong ve Projects. |
| Non-Functional Constraints | Delete la action nguy hiem, khong dat nhu nut chinh noi bat. Khong xoa source goc ngoai he thong quan ly. |

### U029 - Chay demo voi sample project

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U029 |
| Use Case | Chay demo voi sample project |
| Brief Description | Cung cap project mau nho de nguoi khac co the test nhanh parser, index, search, API, graph, va chat. |
| Actor | Nguoi demo, nguoi cham diem, developer setup moi. |
| Pre-Condition | He thong co sample project hoac link tai sample project hop le. |
| Result | User import/index sample project thanh cong va co san cau hoi demo de kiem tra tinh nang. |
| Main Scenario | Buoc 1: User chon Import Sample Project.<br><br>Buoc 2: He thong tao project mau va index.<br><br>Buoc 3: UI hien project card va workspace.<br><br>Buoc 4: He thong goi y demo questions nhu "API login nam o dau?", "module indexing lam gi?", "function nay duoc dung o dau?".<br><br>Buoc 5: User chay search/chat/API/graph theo checklist. |
| Alternative Scenarios | Neu sample da ton tai, he thong cho Open existing, Re-index, hoac Reset sample. |
| Exception Flows | **Sample missing/corrupt:** UI bao loi va huong dan cai lai sample.<br><br>**Index sample failed:** Hien job error de debug. |
| Non-Functional Constraints | Sample project phai nho, on dinh, khong chua secret, va co code du phong phu de demo endpoints/symbols/relations. |

### U030 - Demo checklist va evaluation assistant quality

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U030 |
| Use Case | Demo checklist va evaluation assistant quality |
| Brief Description | Dam bao san pham co the demo lap lai va co cach danh gia chat/search co citation. |
| Actor | Nguoi demo, nguoi cham diem, developer kiem thu. |
| Pre-Condition | Sample project hoac project test da duoc index. |
| Result | User co checklist de test flow chinh va bo cau hoi mau de danh gia assistant. |
| Main Scenario | Buoc 1: User mo Demo Checklist trong docs hoac app.<br><br>Buoc 2: Checklist huong dan import sample, xem project card, mo workspace, search, xem API, chat, evidence, re-index, delete.<br><br>Buoc 3: User chay bo evaluation questions.<br><br>Buoc 4: He thong/nguoi test kiem tra cau tra loi co citation, citation dung file/line, assistant co noi khong du evidence khi can.<br><br>Buoc 5: Ket qua duoc ghi vao test report, evaluation run, hoac release notes neu can. |
| Alternative Scenarios | Evaluation co the chay thu cong hoac automated mot phan.<br><br>Neu LLM khong co, chi danh gia search/evidence/fallback. |
| Exception Flows | **Cau tra loi khong co citation:** Mark failed.<br><br>**Citation sai:** Mark failed va tao issue/parser/retrieval improvement. |
| Non-Functional Constraints | Evaluation khong can qua phuc tap nhung phai lap lai duoc. Docs phai phan anh dung trang thai that. |

### U031 - Multi-user sharing and RBAC (deferred)

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U031 |
| Use Case | User authentication va project access control tuy chon |
| Brief Description | Mo rong sau production v1 thanh multi-user sharing/RBAC. L3 van bat buoc co single-operator authentication, repository authorization boundary va audit; chi sharing/RBAC la deferred. |
| Actor | Project owner, reviewer, developer duoc chia se project. |
| Pre-Condition | He thong co user model va auth/session/token mechanism. |
| Result | Moi user chi xem/chinh sua project minh co quyen. Owner co the chia se project voi reviewer/developer. |
| Main Scenario | Buoc 1: User dang nhap.<br><br>Buoc 2: User xem danh sach project cua minh.<br><br>Buoc 3: Owner chia se project cho email/user khac voi role Viewer, Reviewer, hoac Maintainer.<br><br>Buoc 4: He thong ap dung quyen: Viewer xem/search/chat, Maintainer co the re-index, Owner co the delete/share.<br><br>Buoc 5: UI an action user khong co quyen. |
| Alternative Scenarios | Local single-user mode: bo qua login va access control.<br><br>Reviewer chi co read-only access. |
| Exception Flows | **Session het han:** Yeu cau dang nhap lai.<br><br>**User khong co quyen:** Tra ve forbidden va khong tiet lo project metadata nhay cam. |
| Non-Functional Constraints | Khong ap dung neu baseline/local app khong can multi-user. Neu co, security va ownership phai ro rang truoc khi cloud deployment. |


### U032 - Agentic planner cho cau hoi codebase

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U032 |
| Use Case | Agentic planner cho cau hoi codebase |
| Brief Description | Cho phep assistant phan tich cau hoi cua user, xac dinh muc tieu, lap ke hoach truy xuat evidence, va chon cac tool can dung truoc khi tao cau tra loi. |
| Actor | Developer moi, developer bao tri, reviewer, nguoi demo. |
| Pre-Condition | Project da duoc index. He thong co typed tool noi bo nhu search, file detail, symbol detail, endpoint lookup, graph lookup, impact analysis va evidence validator. |
| Result | Assistant tao mot plan ngan gon, goi tool phu hop, thu thap evidence, va chi tra loi khi co du du lieu hoac noi ro gioi han. |
| Main Scenario | Buoc 1: User dat cau hoi tu nhien, vi du "authentication flow hoat dong nhu the nao?".<br><br>Buoc 2: Planner agent phan loai intent cau hoi: API flow, architecture, dependency, impact, onboarding, debugging, hoac refactor.<br><br>Buoc 3: Planner xac dinh cac tool can goi, vi du endpoint lookup, symbol search, graph traversal, file detail, README search.<br><br>Buoc 4: He thong thuc thi cac tool theo thu tu hop ly va gom evidence.<br><br>Buoc 5: Planner danh gia evidence da du hay chua.<br><br>Buoc 6: Neu du, assistant tao cau tra loi co citation; neu chua du, assistant tim them hoac noi ro khong du evidence. |
| Alternative Scenarios | Cau hoi don gian nhu "file login nam o dau?" co the dung workflow ngan: intent -> endpoint/symbol search -> answer.<br><br>Cau hoi mo hoac mo ho nhu "project nay co on khong?" assistant co the hoi lai de lam ro hoac chuyen thanh architecture overview neu co evidence. |
| Exception Flows | **Planner chon sai tool:** He thong co the fallback sang general search va hien muc confidence thap.<br><br>**Tool loi:** Assistant thong bao tool nao loi va khong duoc bia ket qua.<br><br>**Evidence mau thuan:** Assistant noi ro cac evidence khac nhau va khong ket luan qua chac chan. |
| Non-Functional Constraints | Planner khong duoc thay the evidence bang suy doan LLM. Moi plan/answer phai bi rang buoc boi source code da index va security rules. |

### U033 - Dieu phoi typed tool bang bounded agent workflow

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U033 |
| Use Case | Dieu phoi typed tool bang bounded agent workflow |
| Brief Description | Su dung deterministic state machine voi typed tool de dieu phoi plan, retrieve, verify va answer. Framework nhu LangGraph chi duoc dung sau measured trigger va accepted ADR. |
| Actor | Developer su dung assistant; developer cua he thong muon workflow AI de bao tri va mo rong. |
| Pre-Condition | Cac tool noi bo da co interface ro rang. Workflow co cac node nhu Intent Router, Planner, Search Tool, Graph Tool, Endpoint Tool, Impact Tool, Verifier, Answer Generator. |
| Result | Mot cau hoi phuc tap duoc xu ly bang workflow nhieu buoc co trang thai ro rang, de debug, de mo rong, va co the log trace noi bo. |
| Main Scenario | Buoc 1: User gui cau hoi trong Chat.<br><br>Buoc 2: Deterministic router chon bounded workflow.<br><br>Buoc 3: Chi khi workflow typed khong du, planner tao ke hoach trong budget.<br><br>Buoc 4: Typed tools truy xuat du lieu.<br><br>Buoc 5: Evidence selector hop nhat, loai trung va ap token budget.<br><br>Buoc 6: Sufficiency policy kiem tra evidence.<br><br>Buoc 7: Generator tao claims va citation; validator chap nhan, repair mot lan hoac tra insufficient evidence. |
| Alternative Scenarios | Exact question di thang qua deterministic lookup va evidence, khong planner/vector/provider. Framework workflow chi duoc thay the sau accepted ADR va compatibility tests. |
| Exception Flows | **Workflow loop qua nhieu lan:** He thong dung theo max steps va thong bao chua du evidence.<br><br>**Mot node fail:** Workflow ghi loi node, thu fallback neu co, va khong hien ket qua sai.<br><br>**LLM provider timeout:** Tra ve error/fallback ro rang. |
| Non-Functional Constraints | Workflow trace khong hien raw prompt/API key cho user. Can co max step, timeout, va logging de debug. |

### U034 - Verification agent kiem tra evidence va hallucination

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U034 |
| Use Case | Verification agent kiem tra evidence va hallucination |
| Brief Description | Truoc khi hien cau tra loi, he thong kiem tra xem cac ket luan cua assistant co duoc support boi evidence hay khong. |
| Actor | Developer, reviewer, nguoi demo can cau tra loi dang tin cay. |
| Pre-Condition | Assistant da tao draft answer va co evidence bundle gom file path, line/snippet, symbol/endpoint/graph relation neu co. |
| Result | Cau tra loi cuoi cung chi chua cac ket luan co evidence ro; phan suy luan duoc gan nhan; neu thieu evidence, assistant noi ro. |
| Main Scenario | Buoc 1: Answer Generator tao draft answer dua tren evidence.<br><br>Buoc 2: Verification agent tach cac claim quan trong trong draft.<br><br>Buoc 3: He thong doi chieu moi claim voi evidence: file, line, snippet, endpoint, graph relation.<br><br>Buoc 4: Claim co evidence duoc giu lai va gan citation.<br><br>Buoc 5: Claim khong du evidence bi loai bo, ha muc do chac chan, hoac chuyen thanh "co the"/"can kiem tra them".<br><br>Buoc 6: UI hien cau tra loi da verify va danh sach evidence. |
| Alternative Scenarios | Neu cau hoi la giai thich tong quan, verifier yeu cau it nhat mot nhom evidence dai dien nhu README, entry point, endpoints, models.<br><br>Neu user yeu cau opinion/review, assistant phai tach opinion khoi facts. |
| Exception Flows | **Khong co evidence nao:** Assistant khong tra loi nhu chac chan va goi y user re-index hoac hoi cu the hon.<br><br>**Citation stale:** Verifier canh bao citation thuoc index version cu.<br><br>**Evidence bi secret-skip:** Assistant noi ro noi dung bi skip vi security va khong co quyen suy doan. |
| Non-Functional Constraints | Verifier phai uu tien do tin cay hon do dai cau tra loi. Khong duoc them citation gia. |

### U035 - Agentic investigation cho cau hoi nhieu buoc

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U035 |
| Use Case | Agentic investigation cho cau hoi nhieu buoc |
| Brief Description | Cho phep assistant tu kham pha nhieu phan cua codebase de tra loi cac cau hoi lon nhu authentication flow, indexing pipeline, request flow, refactor plan, hoac performance risk. |
| Actor | Developer moi, developer bao tri, reviewer, tech lead. |
| Pre-Condition | Project da index va co metadata/search/graph/evidence du dung. Agent workflow va LLM provider san sang. |
| Result | Assistant tra loi bang mot investigation report ngan gon: plan, findings, evidence, assumptions, limitations, va suggested next steps. |
| Main Scenario | Buoc 1: User hoi cau hoi phuc tap, vi du "Authentication flow hoat dong nhu the nao?".<br><br>Buoc 2: Planner chia cau hoi thanh sub-tasks: tim endpoint login, tim service xu ly, tim JWT/session logic, tim middleware/dependency, tim protected routes.<br><br>Buoc 3: Workflow goi nhieu tool de lay evidence cho tung sub-task.<br><br>Buoc 4: He thong tao flow summary dua tren evidence theo thu tu xu ly.<br><br>Buoc 5: Verifier kiem tra cac claim va citation.<br><br>Buoc 6: UI hien cau tra loi co cau truc: Overview, Flow steps, Evidence, Risks/Unknowns. |
| Alternative Scenarios | Cau hoi "Toi muon them OAuth2 thi can sua dau?" tao ra change plan dua tren auth-related modules, config, endpoints, tests.<br><br>Cau hoi "Request nay cham o dau?" tim endpoint, database calls, loops, external API calls, va noi ro chi la static analysis neu khong co runtime metrics. |
| Exception Flows | **Graph chua du de trace:** Assistant dung search va file evidence, dong thoi noi ro chua trace day du.<br><br>**Cau hoi qua rong:** Assistant de nghi chia nho hoac tao plan truoc.<br><br>**Evidence qua nhieu:** Assistant summarize va uu tien evidence co lien quan nhat. |
| Non-Functional Constraints | Investigation phai co gioi han buoc, thoi gian, va so evidence de tranh cham. Khong duoc mo rong ra ngoai codebase neu user khong yeu cau. |

### U036 - AI explanation mode va learning path ca nhan hoa

| Thuoc tinh | Noi dung |
| --- | --- |
| Use case ID | U036 |
| Use Case | AI explanation mode va learning path ca nhan hoa |
| Brief Description | Cho phep assistant dien giai codebase theo muc do nguoi dung va bien suggested reading path thanh lo trinh hoc/doc co giai thich de hieu. |
| Actor | Developer moi, sinh vien, reviewer, nguoi demo. |
| Pre-Condition | He thong da co suggested reading path, file/symbol metadata, evidence, va LLM provider neu can tao giai thich tu nhien. |
| Result | User nhan duoc lo trinh doc code co thu tu, muc tieu tung buoc, cau hoi nen tu hoi, va citation den file lien quan. |
| Main Scenario | Buoc 1: User mo Workspace Overview hoac hoi "Toi nen doc project nay nhu the nao?".<br><br>Buoc 2: He thong lay reading path rule-based tu U013.<br><br>Buoc 3: Explanation agent chuyen danh sach file thanh lo trinh: bat dau tu README/entry point, sau do API, model, service, graph/impact neu can.<br><br>Buoc 4: User chon che do giai thich: Beginner, Developer, Reviewer.<br><br>Buoc 5: Assistant tao learning path ngan gon, moi buoc co ly do va evidence.<br><br>Buoc 6: User bam vao tung buoc de mo file detail hoac chat theo context do. |
| Alternative Scenarios | Neu khong co LLM provider, UI van hien reading path co reason/evidence theo rule-based.<br><br>Neu user la reviewer, explanation uu tien architecture, risks, API surface, va dependencies thay vi giai thich tung dong code. |
| Exception Flows | **Reading path confidence thap:** Assistant noi ro day chi la goi y dua tren naming/file tree.<br><br>**LLM loi:** Fallback sang explanation template dua tren metadata.<br><br>**Evidence khong du:** Khong tao lo trinh qua chi tiet. |
| Non-Functional Constraints | LLM chi duoc dien giai dua tren candidate files/evidence da co, khong duoc tu them file khong ton tai. Giai thich phai ngan gon, de hieu, va co citation khi noi ve code. |

## 5. Yeu cau phi chuc nang

### De hieu

Ngon ngu UI phai phuc vu user, khong phuc vu developer noi bo. Neu dung tu nhu "symbol", "chunk", "graph node", he thong phai doi thanh cach dien dat gan voi viec cua user hoac giai thich trong ngu canh phu hop.

### Tin cay

Ket qua assistant phai dua tren evidence. Neu khong co evidence, assistant phai noi ro khong du du lieu. Moi citation nen co file path, line range neu co, snippet, source type, va index version.

### Bao tri duoc

Code can duoc tach theo module ro rang: import, preview, indexing, parser, retrieval, graph, API, frontend pages, frontend components, settings, storage, security. Moi module nen co contract de test va thay doi rieng.

### An toan

He thong khong duoc doc secret files, khong index dependencies lon, khong mo dataset neu user khong yeu cau, khong de path noi bo lam user roi, va khong log credential. Bao mat phai uu tien hon viec index duoc nhieu file.

### Hieu nang

Ban dau he thong co the chay sync voi project nho, nhung huong san pham can background indexing de xu ly project lon. UI phai phan hoi duoc khi indexing dang chay. Search project nho/vua nen phan hoi nhanh va khong lam treo workspace.

### Agentic AI dang tin cay

LLM va agent chi duoc dung de lap ke hoach, chon tool, tong hop, dien giai, va kiem tra cau tra loi dua tren evidence. He thong khong duoc de LLM tu khang dinh file, symbol, endpoint, dependency, hoac impact neu khong co du lieu tu parser/search/graph/evidence. Agent workflow can co max steps, timeout, fallback, va verification truoc khi tra loi.

### Kha nang mo rong

He thong can luu index_version, source_version, parser_version, job history, agent_trace_id, tool_call_summary, va evidence bundle de ho tro re-index, stale citation, sync GitHub, debug agent workflow, va evaluation sau nay.

## 6. Definition of Done cho full product

Full product duoc xem la hoan chinh khi cac nhom kha nang sau co the hoat dong on dinh:

1. Import source tu browser folder upload, ZIP upload, va constrained public Git theo pham vi duoc ho tro; khong nhan backend-local path hoac private/arbitrary Git trong production v1.
2. Preview project truoc khi index, hien file se index, file bi skip, canh bao secret, va duplicate warning.
3. Project card gon, de hieu, khong hien thong tin noi bo gay roi.
4. Indexing status, job history, parser warnings, skipped files, va stale index duoc hien thi ro rang.
5. Re-index chay lap lai duoc, khong tao duplicate records, va co index_version moi.
6. Workspace giup user hieu project: tech stack, modules, important files, symbols, endpoints, suggested reading path.
7. File detail va symbol detail co metadata, snippet, relations, va evidence khi co.
8. Search tim duoc file, symbol, endpoint, dependency, va snippet quan trong; co filter de giam nhieu.
9. Chat tra loi co citation, khong bia khi thieu evidence, va ho tro chat theo context hien tai.
10. Agentic AI workflow co planner, tool orchestration, evidence verification, va investigation mode cho cau hoi nhieu buoc.
11. LLM chi tong hop/dien giai dua tren evidence da truy xuat, khong tu doan file/symbol/flow khong co trong index.
12. Evidence/citation detail co file, line, snippet, source type, index version, va stale warning khi can.
13. API view liet ke endpoints va trace request flow neu co du graph/evidence.
14. Dependency graph hien relation co y nghia: depends on, used by, calls, called by, related endpoints/tests.
15. Impact analysis phan biet evidence-based impact va inferred impact.
16. Security settings bao gom ignore patterns, secret scanning, va provider config an toan.
17. Storage/delete actions khong xoa ngoai pham vi duoc quan ly.
18. Sample project, demo checklist, va bo evaluation questions co the chay lap lai.
19. Backend tests pass cho import, preview, index, re-index, delete, search, chat, citation, security skip, va agentic workflow.
20. Frontend lint/build pass va UI khong hien trang thai sai su that.
21. Test report, evaluation run, hoac release notes phan anh dung trang thai that cua code, ke ca tinh nang chua xong.

## 7. Capability Groups

Phan nay khong gioi han use case va khong ep thu tu trien khai. Cac nhom ben duoi chi giup nhin full product theo cum kha nang de team tu chon uu tien phat trien.

### Group 1 - Core usable product

- U001 - Import project bang folder, zip, git hub.
- U002 - Preview project truoc khi index.
- U003 - Phat hien va xu ly project trung lap.
- U006 - Theo doi tien trinh indexing.
- U007 - Re-index project.
- U010 - Xem workspace tong quan codebase.
- U011 - Xem file explorer va file detail.
- U014 - Tim kiem trong codebase co filter.
- U015 - Xem evidence va citation detail.
- U016 - Chat voi codebase co evidence.
- U028 - Xoa project.
- U029 - Chay demo voi sample project.

### Group 2 - Strong code understanding product

- U008 - Xem indexing job history va parser warnings.
- U009 - Phat hien index da cu so voi source.
- U012 - Xem symbol detail.
- U013 - Goi y diem bat dau doc code.
- U017 - Chat theo context hien tai.
- U018 - Quan ly chat history va citation stale.
- U019 - Xem API endpoints va endpoint detail.
- U020 - Trace request flow.
- U021 - Xem dependency graph thuc dung.

### Group 3 - Advanced assistant product

- U004 - Import GitHub repository.
- U005 - Sync source moi tu GitHub.
- U022 - Impact analysis khi sua file hoac symbol.
- U023 - Tim tests lien quan den code duoc chon.
- U024 - Cau hinh ignore patterns.
- U025 - Secret scanning va canh bao bao mat.
- U026 - Cau hinh LLM va embedding provider.
- U027 - Quan ly storage va du lieu project.
- U030 - Demo checklist va evaluation assistant quality.
- U032 - Agentic planner cho cau hoi codebase.
- U033 - Dieu phoi typed tool bang bounded agent workflow.
- U034 - Verification agent kiem tra evidence va hallucination.
- U035 - Agentic investigation cho cau hoi nhieu buoc.
- U036 - AI explanation mode va learning path ca nhan hoa.

### Group 4 - Optional multi-user/cloud product

- U031 - User authentication va project access control tuy chon.

## 8. Production Capability Additions

These use cases extend the product toward the P0-P2 production roadmap.

### U037 - Xem index quality va validation report

User can inspect whether the latest index is complete enough to trust.

Acceptance criteria:

- UI shows processed files, parser warnings, unresolved references, orphan graph nodes, and dropped edges.
- User can open validation details.
- Critical validation failures block new index activation.
- Warning/coverage diagnostics gan voi `ready` hoac `limited`; `ready_with_warnings` chi la index build status, khong phai capability state.

### U038 - Xem capability readiness theo tung tinh nang

User can see which parts of a repository are ready, limited, failed, or in development.

Acceptance criteria:

- Code Explorer, Search, Graph, Chat, Architecture, and Guided Tours use only `ready`, `limited`, `unavailable`, `failed`, or `stale` as capability states.
- A failed semantic search provider does not block Code Explorer or Graph if they are valid.
- UI shows remediation or re-index action where useful.

### U039 - Xem provenance cua graph relation

User can click a relationship and see why it exists.

Acceptance criteria:

- Relation detail shows origin: parser, resolver, framework rule, heuristic, LLM-inferred, or user-confirmed.
- Relation shows confidence and supporting evidence.
- Inferred relations are clearly labeled.

### U040 - So sanh hai index versions

User can compare old and new index versions after re-index.

Acceptance criteria:

- UI shows added, removed, changed files.
- UI shows changed symbols/endpoints.
- UI shows graph node/edge changes.
- UI shows affected tours or architecture areas.

### U041 - Xem guided tours

User can follow guided tours for learning the repository.

Acceptance criteria:

- Product has at least Project Overview and Backend Request Flow tours.
- Each tour step links to file, graph node, or evidence.
- Each step explains why it comes next.
- Tours never reference missing nodes or deleted files.

### U042 - Xem architecture layers

User can inspect architecture layers, modules, services, configs, and file membership.

Acceptance criteria:

- Layer assignment includes reason and confidence.
- User can open files in a layer.
- Unsupported or inferred layer assignments are labeled.

### U043 - Re-index incremental co affected set

User can run incremental re-index that updates changed files and related dependents.

Acceptance criteria:

- System classifies changes by content, structure, public API, dependency, parser version, embedding version, or enrichment version.
- System expands reanalysis to direct dependents, endpoint chains, tests, and related semantic batches when needed.
- Incremental result is comparable with full rebuild on test fixtures.

### U044 - Xem unresolved references

User can inspect imports, calls, API calls, tests, or config references that could not be resolved.

Acceptance criteria:

- Each unresolved reference has source file, raw reference, type, message, and confidence.
- Unresolved references are counted in index quality.
- User can open the source file.

### U045 - Domain/business flow view

P2 user can inspect business domains and flows inferred from code, docs, endpoints, and models.

Acceptance criteria:

- Domain nodes and flow steps are labeled as deterministic, heuristic, or LLM-inferred.
- Each flow step links to code or evidence when available.
- Unsupported business claims are not shown as confirmed facts.
