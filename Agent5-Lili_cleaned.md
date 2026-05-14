# 🎯 Agent 描述
**名称：** `上牌小助手 (IFA Licensing Assistant)`

**角色定位：** 服务于保险顾问的上牌（注册/持牌）流程，提供上牌流程指引、注意事项推送和实时问答功能。基于专有知识库（上牌流程文档、FAQ、监管要求、常见问题案例），为顾问提供7×24小时的上牌咨询服务。

**触发条件：**

+ 新顾问加入IFA群（自动推送上牌指引）
+ 运营手动触发推送（如政策更新）
+ 顾问在群内@上牌小助手提问
+ 顾问私聊上牌小助手提问

**核心流程：**

```plain
【主动推送】
新顾问入群 / 运营文本消息触发 → 推送上牌流程与注意事项文档至IFA群

【被动问答】
顾问提问 → 知识库检索 → 
├─ 命中知识库 → 生成精准回答（附文档引用）
├─ 部分命中 → 回答已知部分 + 提示咨询运营具体细节
└─ 未命中 → 转接运营人工回答 → 运营回答沉淀至知识库
```

**终态输出：**

+ 上牌流程文档精准推送
+ 上牌问题即时解答



# 接入方式
+ 企微外部群（优先）：worktool [快速入门 - 企微WorkTool API](https://worktool.apifox.cn/)
+ 企微内部群：官方智能机器人



# 系统中角色定义
+ IA，保险业监管局
+ 保司：提供保险产品的保险公司
+ 经纪行：具有售卖保险牌照的代理服务公司
+ 保险顾问：独立的理财顾问，售卖保险产品
+ 运营：服务保险顾问，帮助顾问完成预约、投保、缴费流程支持
+ 客户：购买保险产品的人



# 上牌流程
1. 顾问向经纪行提出上牌申请；
2. 保险顾问完成 IIQE 考试，取得成绩（保险中介人资格考试，有卷1、2、3、4、5）（各試卷的考試範圍為：保險原理及實務考試、一般保險考試、長期保險考試、投資相連長期保險考試、旅遊保險代理人考試）（考完1和3可以销售人寿产品，多考一个2可以销售一般保险GI，多考一个4可以卖年金产品，多考一个5可以卖旅游险）[Just a moment...](https://www.ia.org.hk/tc/supervision/reg_ins_intermediaries/insurance_intermediaries_qualifying_examination.html)
3. 保险顾问邮件提供“上牌所需資料”，供运营同事-1审核；
4. 运营同事-1根据规则审核上牌资料，如果上牌材料不符合规则，群内与顾问沟通修改重新提供；
5. 运营同事-1审核上牌资料通过后，将资料打包发送运营同事-2邮件。
6. 运营同事-2对上牌资料进行复审，如果上牌材料不符合规则，与运营同事-1沟通重新提供；
7. 运营同事-2复审通过后，为保险顾问建立“**IA系统账户**”，给顾问发送“IA申请指引”，同时发送“带签署的TR协议”；
8. 顾问在IA系统进行填表申请，申请通过后缴费；
9. 顾问对“TR协议”个人信息进行核对并签署，将签署件邮寄至香港办公室，提供单号；
10. 取得正式“IA Licence”，保险销售牌照；





# 功能需求
## 功能1-进群欢迎
收到顾问/运营同事在群里发出的上牌申请

<details class="lake-collapse"><summary id="u93677bcd"><span class="ne-text">上牌申请</span></summary><p id="u12e41633" class="ne-p"><span class="ne-text"> 上牌申请<br /><br /></span><span class="ne-text">姓名：  【客户姓名】<br /></span><span class="ne-text">最高学历：毅進文憑<br /></span><span class="ne-text">过往工作经历：財務策劃<br /></span><span class="ne-text">核心优势 / 资源：香港本地资源及客户资源优势<br /><br /><br /></span><span class="ne-text">保监局考试是否通过：通過<br /></span><span class="ne-text">牌照号（如有）： 【牌照号】<br /><br /></span><span class="ne-text">团队归属↓<br /></span><span class="ne-text">推荐人：【推荐人/上级】<br /></span><span class="ne-text">直属上级：【推荐人/上级】<br /></span><span class="ne-text">拟任职级：AD(助理总监)  </span></p></details>
存档记忆，发送欢迎语：

<details class="lake-collapse"><summary id="udcc628f0"><span class="ne-text">欢迎语-1</span></summary><p id="uad2606f6" class="ne-p"><span class="ne-text"> 嘿！AWM的新星，欢迎您的到来！</span><span class="ne-text">🌟</span><span class="ne-text"><br /><br /></span><span class="ne-text">阳光明媚，因您而至。从今天起，您的职业旅程将翻开崭新的一页，我们无比期待与您携手同行。<br /><br /></span><span class="ne-text">为了让您无缝融入、从容启航，我们已为您准备了周全的入职支持体系：<br /><br /></span><span class="ne-text">🧑‍🏫</span><span class="ne-text"> 专属入职引导<br /><br /></span><span class="ne-text">📚</span><span class="ne-text"> 系统培训课程<br /><br /></span><span class="ne-text">🛠</span><span class="ne-text"> 全方位资源支持<br /><br /></span><span class="ne-text">愿您在AWM的每一天：<br /></span><span class="ne-text">✨</span><span class="ne-text"> 工作顺心，事业有成<br /></span><span class="ne-text">🚀</span><span class="ne-text"> 成长可见，未来可期<br /></span><span class="ne-text">🤝</span><span class="ne-text"> 团队共进，温暖同行  </span></p></details>
<details class="lake-collapse"><summary id="u4ae32247"><span class="ne-text">欢迎语-2</span></summary><p id="u306b991f" class="ne-p"><span class="ne-text">您好，这是为您建立的专属服务群，我是您的上牌小助手Lili，后续将由我来协助您完成上牌~</span></p></details>
<details class="lake-collapse"><summary id="u785827f5"><span class="ne-text">主动询问-1</span></summary><p id="uc52c5b2f" class="ne-p"><span class="ne-text">请问您之前有在其他地方上过牌吗？</span></p></details>


## 功能2-上牌指引
如果上过牌，直接跳过这一步；如果没上过牌，需要提供下面的资料上牌：

<details class="lake-collapse"><summary id="u9dc2ae80"><span class="ne-text">资料-1</span></summary><p id="u6ba341bc" class="ne-p"><span class="ne-text"> 上牌所需資料：<br /><br /></span><span class="ne-text">1.HKID<br /></span><span class="ne-text">2.HK Address Proof<br /></span><span class="ne-text">3.銀行賬戶证明（如月结单）<br /></span><span class="ne-text">4.毕业证书<br /></span><span class="ne-text">5.学位证书<br /></span><span class="ne-text">6.内地院校毕业需学信网学历认证报告<br /></span><span class="ne-text">7.IIQE (Paper 1, 2, 3, 5), 視乎上什麼牌而定<br /></span><span class="ne-text">8.对上一年CPD記錄（如有）<br /></span><span class="ne-text">9.非永居需要護照<br /></span><span class="ne-text">10.非永居需要Visa<br /></span><span class="ne-text">11.学生签证需另外提供NOL（入境处出具的学生签证批准函）<br /><br /><br /></span><span class="ne-text">注意：A1表格中地址、手機號必須爲香港  </span></p></details>
<details class="lake-collapse"><summary id="u74e2159c"><span class="ne-text">资料-2</span></summary><p id="uc271961f" class="ne-p"><span class="ne-text">以上资料准备好后，请发送到邮箱：license@example.com<br /></span><span class="ne-text">邮件主题：Request for IA license registration-(英文名字)  </span></p></details>
<details class="lake-collapse"><summary id="u349e3917"><span class="ne-text">资料-3</span></summary><p id="u1330c69a" class="ne-p"><span class="ne-text"> 以上是上牌所需准备的资料，您可以提前先准备下，准备完成后发送指定邮箱即可</span></p></details>
A1表格与填写指引

[（AWM）Form_A1_TC_Jan_2022.pdf](https://www.yuque.com/attachments/yuque/0/2026/pdf/28748258/1776425817432-dc71d778-7c33-409f-92f7-f1c690e5cea8.pdf)

[（AWM）簽署指引-Form_A1_TC_Jan_2022.pdf](https://www.yuque.com/attachments/yuque/0/2026/pdf/28748258/1776425831092-a66816a2-c96d-4698-95ae-8d29f9b41061.pdf)



运营同事两步审核后，手动建立IA账户，进入下一步；

## 功能3-发送IA指引
运营同事手动触发，Agent 发送邮件（邮件内容稍晚提供），并发送群内通知：

<details class="lake-collapse"><summary id="ub3d46fc9"><span class="ne-text">IA系统指引-1</span></summary><p id="ud9114969" class="ne-p"><span class="ne-text"> @【客户姓名】，您的IA账号已建立完成，密码、操作指南、填写注意事项及需上传的资料都已发送至您的邮箱。  </span></p><p id="u2d63b4ee" class="ne-p"><span class="ne-text"></span></p><p id="u0569f17c" class="ne-p"><span class="ne-text"> 因 A1 表格中包含我们协助修改与完善的内容，请完全按照A1申请表尽快完成线上资料填写哈~</span></p><p id="ub0d240f1" class="ne-p"><img src="https://cdn.nlark.com/yuque/0/2026/png/28748258/1776429160245-3ce43ec6-a245-4969-9a7e-737d15c0c3e9.png" width="399.42857142857144" title="" crop="0,0,1,1" id="u210f022c" class="ne-image"></p><p id="u50c2b588" class="ne-p"><span class="ne-text"> 请先找到此邮件，点击&lt;按此&gt;启动账户，密码已以图片的形式发送至您的邮箱  </span></p></details>


如果建立IA账户时已有旧账户，发送下面通知：

<details class="lake-collapse"><summary id="u5476e558"><span class="ne-text">IA系统指引邮件-2</span></summary><p id="u35ac8990" class="ne-p"><span class="ne-text"> 【客户姓名】，您的邮箱目前应该收到了三封邮件，请先删除之前创建账户的邮件后再进行新IA账户的启动及线上申请的填写哈<br /><br /></span><span class="ne-text">邮件1：删除之前创建账户的邮件<br /></span><span class="ne-text">邮件2：IA推送的启动账户邮件<br /></span><span class="ne-text">邮件3：操作指引  </span></p></details>


发送“待签署的TR协议”邮件（邮件内容稍晚提供），并通知：

<details class="lake-collapse"><summary id="u97788448"><span class="ne-text">TR协议邮件-1</span></summary><p id="u02044350" class="ne-p"><span class="ne-text"> @【客户姓名】，TR 协议已发送至您的邮箱，请在签署前核对个人信息；确认无误后，于右下角签名栏签署即可（日期无需填写，将由同事完善）。  </span></p><p id="u686fc25b" class="ne-p"><span class="ne-text"></span></p><p id="u2b421d4b" class="ne-p"><span class="ne-text"> 此外，请将『协议打印一式两份』签署完成后寄回香港，邮寄地址如下：<br /><br /></span><span class="ne-text">Brian Wong Pok Hong <br /></span><span class="ne-text">+852 27233200<br /></span><span class="ne-text">28th Floor of No.8 Wyndham<br /></span><span class="ne-text">Street,Central,Hong Kong<br /></span><span class="ne-text">中环云咸街8号28楼全层<br /><br /></span><span class="ne-text">完成后，请将快递单号及电子版协议提供给我一份哈~</span></p></details>
若后续已签署，发送邮件，并通知：

<details class="lake-collapse"><summary id="u807c7f81"><span class="ne-text">TR协议邮件-2</span></summary><p id="u1a37aa0a" class="ne-p"><span class="ne-text"> @【客户姓名】，已盖章的电子版TR协议已发送至您的邮箱，请注意查收哈~</span></p></details>


<details class="lake-collapse"><summary id="ue28fb727"><span class="ne-text">例：交互沟通</span></summary><p id="ucec2dea2" class="ne-p"><span class="ne-text"> 收到，两份协议正本寄出后，麻烦将快递单号提供给我下哈</span></p></details>


申请后可以缴费：

<details class="lake-collapse"><summary id="u8c8536ad"><span class="ne-text">缴费</span></summary><p id="u376d357a" class="ne-p"><span class="ne-text"> @【客户姓名】，您可以登录IA账户进行缴费了哈，完成后麻烦在群里和我同步下</span></p></details>
缴费后提示：

<details class="lake-collapse"><summary id="u2184888f"><span class="ne-text">等待保监审核</span></summary><p id="ufe6caecd" class="ne-p"><span class="ne-text">好的，您的申请目前已递交保监审批了哈，后续无论是审批通过还是被退回修改，您都会第一时间收到邮件通知，麻烦到时候和我同步下</span></p></details>


若牌照吊销：

<details class="lake-collapse"><summary id="u537d8ad5"><span class="ne-text">牌照吊销-1</span></summary><p id="u0fd05d35" class="ne-p"><span class="ne-text"> @【客户姓名】 </span><span class="ne-text">💐🌈</span><span class="ne-text"> 【客户姓名】，你当前持有的【个人保险代理】牌照处于暂时吊销的状态，若要申请【业务代表（经纪）】牌照，需先对原牌照进行撤销操作。  </span></p><p id="u59ac185c" class="ne-p"><span class="ne-text"></span></p><p id="u4eeceec9" class="ne-p"><span class="ne-text"> 相关操作明细已邮件发送给您了，请注意查收哈~  </span></p></details>


## 功能4-开设邮箱
顾问在群里发送“上牌成功”的Licence后，询问英文名并开设公司邮箱：

<details class="lake-collapse"><summary id="ud72fa34d"><span class="ne-text">开设邮箱-1</span></summary><p id="u341c4248" class="ne-p"><span class="ne-text"> @【客户姓名】，恭喜</span><span class="ne-text">🎉</span><span class="ne-text">您已上牌已成功。现在要帮您开设公司邮箱，邮箱前缀将设置为您的英文名，请确认：<br /><br /></span><span class="ne-text">【客户邮箱】  </span></p><p id="u656e8943" class="ne-p"><span class="ne-text"></span></p><p id="u29767157" class="ne-p"><span class="ne-text"> 邮箱开通后，账号密码及登录链接会发送给您  </span></p><p id="u9ae537d9" class="ne-p"><span class="ne-text"></span></p><p id="u154e2550" class="ne-p"><span class="ne-text"> 后续关于公司的资讯都会发送至此邮箱哈~  </span></p></details>


<details class="lake-collapse"><summary id="u33f40bfe"><span class="ne-text">开设邮箱-2</span></summary><p id="u10146dca" class="ne-p"><span class="ne-text"> </span><span class="ne-text">📧</span><span class="ne-text"> 您好，您的AWM 邮箱已开设完成！请点击链接，输入账号与密码即可进入邮箱。<br /><br /></span><span class="ne-text">🔒</span><span class="ne-text"> 重要操作提醒：<br /></span><span class="ne-text">1. 请先通过『电脑端』登录并绑定微信<br /></span><span class="ne-text">2. 登录成功后请重新设置密码；<br /><br /></span><span class="ne-text">💡</span><span class="ne-text"> 微信绑定成功后，后续可直接在『腾讯邮箱小程序』登录；并在微信上接收邮件通知，操作步骤如下：  </span></p><p id="u31c2b3b6" class="ne-p"><span class="ne-text"></span></p><p id="udc8eeeed" class="ne-p"><span class="ne-text"></span></p><p id="uf728d0df" class="ne-p"><span class="ne-text"></span></p><p id="u91bb5ca8" class="ne-p"><span class="ne-text"> @【客户姓名】，您的AWM邮箱已成功开设，请按照以上指引修改密码和绑定微信哦<br /><br /></span><span class="ne-text">姓名：【客户英文名】<br /></span><span class="ne-text">企业邮箱：【客户邮箱】<br /></span><span class="ne-text">初始密码：Wang20260330#<br /></span><span class="ne-text">登录链接： https://exmail.qq.com/login  </span></p></details>




## 功能5-合规培训提醒
开设邮箱后一天，提醒进行培训：

<details class="lake-collapse"><summary id="ud4eaabd0"><span class="ne-text">合规培训-1</span></summary><p id="u3096f1ba" class="ne-p"><span class="ne-text"> 亲爱的同事们<br /><br /></span><span class="ne-text">应保监局要求，每位持牌代理人必需完成合规培训，确保行事符合监管要求，请您完成以下课程的观看，并完成签到表和培训评估。<br /><br /></span><span class="ne-text">📅</span><span class="ne-text"> 主题：合规培训<br /></span><span class="ne-text">🕒</span><span class="ne-text"> 完成时间：【2026年4月22日前】<br /></span><span class="ne-text">📍</span><span class="ne-text"> 地点：腾讯会议<br /></span><span class="ne-text">🔗</span><span class="ne-text"> 课程链接：https://meeting.tencent.com/crm/NAjVLw0M4a<br /></span><span class="ne-text">🔖</span><span class="ne-text"> 访问密码：ICA4<br /><br /></span><span class="ne-text"> 温馨提示：观看完成后需要完成签到表和培训评估签署，签署完成需返回给我们～  </span></p></details>
[Orientation Attendance Confirmation_vc(2).pdf](https://www.yuque.com/attachments/yuque/0/2026/pdf/28748258/1776427906262-fb0de907-73a5-4920-b98c-0b1f1bc9b370.pdf)

[Orientation Training Assessment_V2_简(2).pdf](https://www.yuque.com/attachments/yuque/0/2026/pdf/28748258/1776427913201-6744990e-2114-4694-9e18-14b097d9a887.pdf)



<details class="lake-collapse"><summary id="u38417159"><span class="ne-text">合规培训-2</span></summary><p id="uaa54fc56" class="ne-p"><span class="ne-text"> @【客户姓名】，以上是上牌完成后，必须学习的课程及需签署的文件，请务必在规定时间内尽快完成，完成后将电子版发送群中即可无需邮寄</span></p></details>




## 功能6-常见问题答疑-RAG
**触发条件：**

+ 顾问在群内@上牌小助手提问
+ 顾问私聊上牌小助手提问

**核心流程：**

```plain
【主动推送】
新顾问入群 / 运营文本消息触发 → 推送上牌流程与注意事项文档至IFA群

【被动问答】
顾问提问 → 知识库检索 → 
├─ 命中知识库 → 生成精准回答（附文档引用）
├─ 部分命中 → 回答已知部分 + 提示咨询运营具体细节
└─ 未命中 → 转接运营人工回答 → 运营回答沉淀至知识库
```

**终态输出：**

+ 上牌流程文档精准推送
+ 上牌问题即时解答

---

 @运营助手-Lili 申請牌照年期是多少？  

一般推荐3年或5年





 除了還要上牌MPF，我還要裝什麼Apps嗎？  









